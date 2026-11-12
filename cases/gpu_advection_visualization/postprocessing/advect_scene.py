"""ParaView scene for the t8code advection example on the hybrid hypercube.

Tested with ParaView 5.11.2 (Ubuntu package, /usr/bin/pvpython). Run it with a clean
library path, otherwise pvpython picks up libraries from the module system:

  env -u LD_LIBRARY_PATH -u PYTHONPATH pvpython advect_scene.py state  <data_dir> <out.pvsm>
  env -u LD_LIBRARY_PATH -u PYTHONPATH pvpython advect_scene.py render <data_dir> <out_dir> <first> <last> [stride] [--raytrace]
      [--inset] [--inset-zoom=Z] [--inset-iso=transparent|curve] [--labels] [--subtitle=TEXT]

'state' writes a ParaView state file for the GUI. 'render' writes one PNG per time step
(frame_NNN.png) for the steps first, first+stride, ... up to last (inclusive). With --inset each frame also
gets a zoom into the refinement band in the bottom left corner, with --labels the text overlays.
--subtitle replaces the second text line (it describes the GPU run), an empty TEXT leaves it out.
Several render processes with disjoint step ranges can run at the same time, see make_video.sh.
The inset and the labels need PIL (Pillow) in pvpython.
"""
import builtins
import glob
import math
import os
import re
import sys

from paraview.simple import *

# Scene parameters
RESOLUTION = [1080, 1350]
# Cutting plane, normal (0,1,1). In run e8u3l2r5c01t1a10v50 the sphere center stays at
# y+z = 1.18..1.24, so the half sphere sits on the cut face for the whole run.
# (Test run e8u3l2r5c01t01: origin (0.6,0.6,0.6), normal (1,1,0).)
PLANE_ORIGIN = [0.5, 0.605, 0.605]
PLANE_NORMAL = [0.0, 1.0, 1.0]
# Uniform grid for the interface contour, covers the sphere path of both runs.
ISO_BOUNDS = [0.12, 0.95, 0.12, 0.95, 0.12, 0.95]
ISO_DIMENSIONS = [256, 256, 256]
# Gaussian smoothing of the resampled phi (standard deviation in voxels), removes the ripples
# that the jumps of phi at hanging faces leave in the interface.
ISO_SMOOTH_SIGMA = 4.0
# Fixed symmetric color range of the level set (sphere radius is about 0.25).
PHI_RANGE = 0.25
BACKGROUND = [0.075, 0.08, 0.09]
EDGE_COLOR = [0.22, 0.22, 0.22]
ISO_COLOR = [0.93, 0.92, 0.88]
OUTLINE_COLOR = [0.42, 0.42, 0.42]
# The cube is framed so that it stays clear of the two text lines at the top and the inset with its label.
CAMERA_POSITION = [3.581, 3.071, 3.811]
CAMERA_FOCAL_POINT = [0.803, 0.446, 0.270]
CAMERA_VIEW_UP = [0.0, 0.0, 1.0]
CAMERA_VIEW_ANGLE = 30.0
# Zoom into the refinement band (inset in the bottom left corner of the frame, option --inset).
# The inset camera looks in the same direction as the main camera at a point on the cut face:
# the point of the interface on the cutting plane that lies farthest in the in-plane direction
# INSET_DIRECTION, moved by INSET_GAP further out. So it follows the sphere and its deformation.
# The zoomed region is marked by a frame in the main image, connected to the inset by two lines.
INSET_RESOLUTION = [360, 360]
# Top left corner of the inset border in the frame. The inset stays clear of the bottom of the frame,
# where video players show their controls.
INSET_POSITION = [40, 800]
# Lower left of the sphere in the main image (hexahedral part of the mesh).
INSET_DIRECTION = [0.962, 0.193, -0.193]
INSET_GAP = 0.005
# Magnification of the inset relative to the main image (pixel size of a feature in the inset / in the main image).
INSET_ZOOM = 10.0
INSET_LINE_COLOR = (176, 176, 176)
INSET_LINE_WIDTH = 2
# Ambient light of the interface in the inset, the zoomed side of the sphere is in the shade.
INSET_ISO_AMBIENT = 0.4
# How the interface is shown in the inset, so that the elements behind it stay visible:
# "transparent" (the sphere with opacity INSET_ISO_OPACITY) or "curve" (only the intersection of the
# interface with the cutting plane, as a line of width INSET_CURVE_WIDTH).
INSET_ISO_MODE = "transparent"
INSET_ISO_OPACITY = 0.4
INSET_CURVE_WIDTH = 6.0

# Text overlays (option --labels): (text, font file, size in px, color, position of the top left corner).
FONT_DIR = "/usr/share/fonts/truetype/roboto/hinted"
LABEL_TITLE = ("t8code - adaptive mesh refinement on a hybrid mesh", "Roboto-Medium.ttf", 40, (240, 240, 240), (40, 30))
LABEL_SUBTITLE = ("Solver loop: AMD GPU (OpenMP offload) - Mesh adaptation: CPU", "Roboto-Regular.ttf", 30,
                  (190, 190, 190), (40, 84))
# Shown with the inset, below it.
LABEL_INSET = ("Refinement follows interface", "Roboto-Regular.ttf", 30, (190, 190, 190), (40, 1178))


def data_files(data_dir):
  """The time series advection_NNN.pvtu, without advection_cmesh*.pvtu."""
  files = glob.glob(os.path.join(os.path.abspath(data_dir), "advection_*.pvtu"))
  files = [f for f in files if re.fullmatch(r"advection_\d+\.pvtu", os.path.basename(f))]
  return sorted(files, key=lambda f: int(re.findall(r"\d+", os.path.basename(f))[0]))


def build_scene(files, raytrace=False):
  """Build the pipeline and the render view. Returns (reader, view)."""
  reader = XMLPartitionedUnstructuredGridReader(registrationName="advection", FileName=files)
  reader.CellArrayStatus = ["Num. Solution", "Ana. Solution", "Error", "level", "treeid", "mpirank"]
  reader.PointArrayStatus = []

  # Mesh, crinkle-clipped so that whole elements remain. Invert keeps the side behind the normal.
  mesh_clip = Clip(registrationName="mesh_crinkle_clip", Input=reader)
  mesh_clip.ClipType = "Plane"
  mesh_clip.ClipType.Origin = PLANE_ORIGIN
  mesh_clip.ClipType.Normal = PLANE_NORMAL
  mesh_clip.Crinkleclip = 1
  mesh_clip.Invert = 1

  # Interface phi = 0. Num. Solution_points holds the constant element value on per-element
  # point copies, so it has no zero crossing inside an element. Merge the points and average
  # the cell values to the points instead. A contour directly on this grid has cracks at the
  # hanging faces, so resample it to a uniform grid around the sphere path first.
  merged = MergeBlocks(registrationName="merge", Input=reader)
  cleaned = CleantoGrid(registrationName="clean_to_grid", Input=merged)
  phi_points = CellDatatoPointData(registrationName="phi_to_points", Input=cleaned)
  phi_points.ProcessAllArrays = 0
  phi_points.CellDataArraytoprocess = ["Num. Solution"]
  resampled = ResampleToImage(registrationName="phi_resampled", Input=phi_points)
  resampled.UseInputBounds = 0
  resampled.SamplingBounds = ISO_BOUNDS
  resampled.SamplingDimensions = ISO_DIMENSIONS
  phi_smooth = ProgrammableFilter(registrationName="phi_gaussian_smooth", Input=resampled)
  phi_smooth.OutputDataSetType = "Same as Input"
  phi_smooth.Script = """
from vtkmodules.vtkImagingGeneral import vtkImageGaussianSmooth
image = vtk.vtkImageData()
image.ShallowCopy(self.GetInputDataObject(0, 0))
image.GetPointData().SetActiveScalars("Num. Solution")
smooth = vtkImageGaussianSmooth()
smooth.SetInputData(image)
smooth.SetDimensionality(3)
smooth.SetStandardDeviations(%g, %g, %g)
smooth.SetRadiusFactors(3, 3, 3)
smooth.Update()
self.GetOutputDataObject(0).ShallowCopy(smooth.GetOutput())
""" % ((ISO_SMOOTH_SIGMA,) * 3)
  iso = Contour(registrationName="interface_phi0", Input=phi_smooth)
  iso.ContourBy = ["POINTS", "Num. Solution"]
  iso.Isosurfaces = [0.0]
  iso.ComputeScalars = 0
  # Normals from the geometry give a cleaner shading than those from the phi gradient.
  iso.ComputeNormals = 0
  # Keep only the part on the cut-away side, so the half sphere sits on the cut face.
  iso_normals = GenerateSurfaceNormals(registrationName="interface_normals", Input=iso)
  iso_normals.FeatureAngle = 90.0
  iso_clip = Clip(registrationName="interface_cut_side", Input=iso_normals)
  iso_clip.ClipType = "Plane"
  iso_clip.ClipType.Origin = PLANE_ORIGIN
  iso_clip.ClipType.Normal = PLANE_NORMAL
  iso_clip.Invert = 0

  outline = Outline(registrationName="cube_outline", Input=reader)

  # Alternative coloring by element type (hidden). CellTypes is only available on a single
  # unstructured grid, not on the partitioned collection, hence the MergeBlocks.
  mesh_clip_merged = MergeBlocks(registrationName="mesh_clip_merged", Input=mesh_clip)
  cell_type = PythonCalculator(registrationName="element_type", Input=mesh_clip_merged)
  cell_type.Expression = "numpy.array(inputs[0].CellTypes, dtype=numpy.int32)"
  cell_type.ArrayAssociation = "Cell Data"
  cell_type.ArrayName = "element_type"

  view = CreateView("RenderView")
  view.ViewSize = RESOLUTION
  view.Background = BACKGROUND
  view.UseColorPaletteForBackground = 0
  view.OrientationAxesVisibility = 0
  view.UseFXAA = 1
  if raytrace:
    view.EnableRayTracing = 1
    view.BackEnd = "OSPRay raycaster"
    view.AmbientSamples = 4
    view.SamplesPerPixel = 4
  SetActiveView(view)

  phi_lut = GetColorTransferFunction("NumSolution")
  phi_lut.ApplyPreset("Cool to Warm", True)
  phi_lut.AutomaticRescaleRangeMode = "Never"
  phi_lut.RescaleTransferFunction(-PHI_RANGE, PHI_RANGE)
  GetOpacityTransferFunction("NumSolution").RescaleTransferFunction(-PHI_RANGE, PHI_RANGE)

  mesh_rep = Show(mesh_clip, view)
  mesh_rep.SetRepresentationType("Surface With Edges")
  ColorBy(mesh_rep, ("CELLS", "Num. Solution"))
  mesh_rep.LookupTable = phi_lut
  mesh_rep.EdgeColor = EDGE_COLOR
  mesh_rep.LineWidth = 1.0
  mesh_rep.SetScalarBarVisibility(view, False)

  iso_rep = Show(iso_clip, view)
  iso_rep.SetRepresentationType("Surface")
  iso_rep.ColorArrayName = [None, ""]
  iso_rep.AmbientColor = ISO_COLOR
  iso_rep.DiffuseColor = ISO_COLOR
  iso_rep.Specular = 0.3
  iso_rep.SpecularPower = 40.0

  outline_rep = Show(outline, view)
  outline_rep.ColorArrayName = [None, ""]
  outline_rep.AmbientColor = OUTLINE_COLOR
  outline_rep.DiffuseColor = OUTLINE_COLOR
  outline_rep.LineWidth = 1.0

  type_rep = Show(cell_type, view)
  type_rep.SetRepresentationType("Surface With Edges")
  # The array only exists after the pipeline ran, so set it directly instead of ColorBy.
  type_rep.ColorArrayName = ["CELLS", "element_type"]
  type_lut = GetColorTransferFunction("element_type")
  type_lut.InterpretValuesAsCategories = 1
  type_lut.Annotations = ["10", "Tetrahedron", "12", "Hexahedron", "13", "Prism", "14", "Pyramid"]
  type_lut.IndexedColors = [0.89, 0.47, 0.20,  0.30, 0.55, 0.75,  0.40, 0.70, 0.40,  0.75, 0.45, 0.70]
  type_rep.LookupTable = type_lut
  type_rep.EdgeColor = EDGE_COLOR
  type_rep.SetScalarBarVisibility(view, False)
  Hide(cell_type, view)

  # Helper filters are not shown.
  for proxy in (reader, merged, cleaned, phi_points, resampled, phi_smooth, iso, iso_normals, mesh_clip_merged):
    Hide(proxy, view)

  view.CameraPosition = CAMERA_POSITION
  view.CameraFocalPoint = CAMERA_FOCAL_POINT
  view.CameraViewUp = CAMERA_VIEW_UP
  view.CameraViewAngle = CAMERA_VIEW_ANGLE
  view.CameraParallelProjection = 0

  scene = GetAnimationScene()
  scene.UpdateAnimationUsingDataTimeSteps()
  scene.PlayMode = "Snap To TimeSteps"
  SetActiveSource(mesh_clip)
  return reader, view


def vec_dot(a, c):
  """Dot product of two 3D vectors (paraview.simple shadows the builtin sum)."""
  return a[0] * c[0] + a[1] * c[1] + a[2] * c[2]


def vec_normalized(a):
  length = vec_dot(a, a) ** 0.5
  return [x / length for x in a]


def convex_hull(points):
  """Indices of the convex hull of 2D points (monotone chain)."""
  order = sorted(range(len(points)), key=lambda i: points[i])
  def cross(o, a, b):
    return (points[a][0] - points[o][0]) * (points[b][1] - points[o][1]) \
        - (points[a][1] - points[o][1]) * (points[b][0] - points[o][0])
  hull = []
  for sweep in (order, order[::-1]):
    part = []
    for i in sweep:
      while len(part) >= 2 and cross(part[-2], part[-1], i) <= 0:
        part.pop()
      part.append(i)
    hull += part[:-1]
  return set(hull)


def save_inset(view, time, inset_file, zoom=INSET_ZOOM, iso_mode=INSET_ISO_MODE):
  """Render the zoom into the refinement band at the given time into inset_file.
  Returns the corners of the zoomed region in the main image (top left, top right, bottom right, bottom left)."""
  from paraview import servermanager
  # Intersection curve of the interface with the cutting plane (not part of the state file).
  section = FindSource("interface_on_plane")
  if section is None:
    section = Slice(registrationName="interface_on_plane", Input=FindSource("interface_phi0"))
    section.SliceType = "Plane"
    section.SliceType.Origin = PLANE_ORIGIN
    section.SliceType.Normal = PLANE_NORMAL
    curve_rep = Show(section, view)
    curve_rep.ColorArrayName = [None, ""]
    curve_rep.AmbientColor = ISO_COLOR
    curve_rep.DiffuseColor = ISO_COLOR
    curve_rep.LineWidth = INSET_CURVE_WIDTH
    curve_rep.RenderLinesAsTubes = 1
    curve_rep.Visibility = 0
  section.UpdatePipeline(time)
  points = servermanager.Fetch(section).GetPoints()
  outermost = builtins.max((points.GetPoint(i) for i in range(points.GetNumberOfPoints())),
                  key=lambda p: vec_dot(p, INSET_DIRECTION))
  focal = [outermost[i] + INSET_GAP * INSET_DIRECTION[i] for i in range(3)]
  # Camera basis: back (towards the camera), up and right.
  back = vec_normalized([CAMERA_POSITION[i] - CAMERA_FOCAL_POINT[i] for i in range(3)])
  up = vec_normalized([CAMERA_VIEW_UP[i] - vec_dot(CAMERA_VIEW_UP, back) * back[i] for i in range(3)])
  right = [up[1] * back[2] - up[2] * back[1], up[2] * back[0] - up[0] * back[2], up[0] * back[1] - up[1] * back[0]]

  # Same view angle as the main camera, so the camera distance gives the magnification.
  main_distance = vec_dot([CAMERA_POSITION[i] - CAMERA_FOCAL_POINT[i] for i in range(3)], back)
  distance = main_distance * INSET_RESOLUTION[1] / (RESOLUTION[1] * zoom)

  view.CameraFocalPoint = focal
  view.CameraPosition = [focal[i] + distance * back[i] for i in range(3)]
  iso_rep = GetDisplayProperties(FindSource("interface_cut_side"), view)
  curve_rep = GetDisplayProperties(section, view)
  iso_rep.Ambient = INSET_ISO_AMBIENT
  if iso_mode == "curve":
    iso_rep.Visibility = 0
    curve_rep.Visibility = 1
  else:
    iso_rep.Opacity = INSET_ISO_OPACITY
  SaveScreenshot(inset_file, view, ImageResolution=INSET_RESOLUTION, CompressionLevel="3")
  iso_rep.Ambient = 0.0
  iso_rep.Opacity = 1.0
  iso_rep.Visibility = 1
  curve_rep.Visibility = 0
  view.CameraPosition = CAMERA_POSITION
  view.CameraFocalPoint = CAMERA_FOCAL_POINT

  half = distance * math.tan(math.radians(CAMERA_VIEW_ANGLE / 2))
  camera = view.GetActiveCamera()
  matrix = camera.GetCompositeProjectionTransformMatrix(RESOLUTION[0] / RESOLUTION[1], -1, 1)
  region = []
  for sx, sy in ((-1, 1), (1, 1), (1, -1), (-1, -1)):
    p = [focal[i] + half * (sx * right[i] + sy * up[i]) for i in range(3)] + [1.0]
    q = [sum_row(matrix, row, p) for row in range(4)]
    region.append(((q[0] / q[3] + 1) / 2 * RESOLUTION[0], (1 - q[1] / q[3]) / 2 * RESOLUTION[1]))
  return region


def compose_frame(frame_file, inset_file=None, region=None, labels=False, subtitle=None):
  """Add the inset (with the frame around the zoomed region and the connecting lines) and the labels to the frame."""
  from PIL import Image, ImageDraw, ImageFont
  frame = Image.open(frame_file).convert("RGB")
  if inset_file:
    # Corners of the inset, with a border of INSET_LINE_WIDTH around the image.
    x0, y0 = INSET_POSITION
    x1 = x0 + INSET_RESOLUTION[0] + 2 * INSET_LINE_WIDTH - 1
    y1 = y0 + INSET_RESOLUTION[1] + 2 * INSET_LINE_WIDTH - 1
    box = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    # Draw the lines supersampled, so that they are antialiased after downsampling.
    scale = 4
    overlay = Image.new("L", (RESOLUTION[0] * scale, RESOLUTION[1] * scale), 0)
    draw = ImageDraw.Draw(overlay)
    def scaled(points):
      return [(x * scale, y * scale) for x, y in points]
    draw.line(scaled(region + region[:1]), fill=255, width=INSET_LINE_WIDTH * scale, joint="curve")
    # Connect the corresponding corners that lie on the outside of both rectangles.
    hull = convex_hull(region + box)
    for i in range(4):
      if i in hull and i + 4 in hull:
        draw.line(scaled([region[i], box[i]]), fill=255, width=INSET_LINE_WIDTH * scale)
    draw.rectangle(scaled([box[0], box[2]]), fill=255)
    overlay = overlay.resize(RESOLUTION, Image.LANCZOS)
    frame.paste(Image.new("RGB", RESOLUTION, INSET_LINE_COLOR), (0, 0), overlay)
    frame.paste(Image.open(inset_file).convert("RGB"), (x0 + INSET_LINE_WIDTH, y0 + INSET_LINE_WIDTH))
  if labels:
    draw = ImageDraw.Draw(frame)
    title_lines = [LABEL_TITLE, LABEL_SUBTITLE if subtitle is None else (subtitle,) + LABEL_SUBTITLE[1:]]
    for text, font_file, size, color, position in title_lines + ([LABEL_INSET] if inset_file else []):
      if text:
        font = ImageFont.truetype(os.path.join(FONT_DIR, font_file), size)
        draw.text(position, text, font=font, fill=color)
  frame.save(frame_file, compress_level=3)


def sum_row(matrix, row, p):
  return (matrix.GetElement(row, 0) * p[0] + matrix.GetElement(row, 1) * p[1]
          + matrix.GetElement(row, 2) * p[2] + matrix.GetElement(row, 3) * p[3])


def main():
  mode, data_dir = sys.argv[1], sys.argv[2]
  files = data_files(data_dir)
  raytrace = "--raytrace" in sys.argv
  inset = "--inset" in sys.argv
  labels = "--labels" in sys.argv
  zoom = INSET_ZOOM
  iso_mode = INSET_ISO_MODE
  subtitle = None
  for arg in sys.argv:
    if arg.startswith("--subtitle="):
      subtitle = arg[len("--subtitle="):]
    if arg.startswith("--inset-zoom="):
      zoom = float(arg.split("=")[1])
    if arg.startswith("--inset-iso="):
      iso_mode = arg.split("=")[1]
  reader, view = build_scene(files, raytrace)
  if mode == "state":
    SaveState(sys.argv[3])
    return
  out_dir = sys.argv[3]
  first, last = int(sys.argv[4]), int(sys.argv[5])
  stride = int(sys.argv[6]) if len(sys.argv) > 6 and sys.argv[6].isdigit() else 1
  scene = GetAnimationScene()
  times = reader.TimestepValues
  for step in range(first, last + 1, stride):
    scene.AnimationTime = times[step]
    frame_file = os.path.join(out_dir, "frame_%03d.png" % step)
    SaveScreenshot(frame_file, view, ImageResolution=RESOLUTION, CompressionLevel="3")
    inset_file, region = None, None
    if inset:
      inset_file = os.path.join(out_dir, "inset_%03d.png" % step)
      region = save_inset(view, times[step], inset_file, zoom, iso_mode)
    if inset or labels:
      compose_frame(frame_file, inset_file, region, labels, subtitle)
    if inset_file:
      os.remove(inset_file)
    print("frame %d done" % step, flush=True)


if __name__ == "__main__":
  main()
