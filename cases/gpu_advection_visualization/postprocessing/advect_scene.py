"""ParaView scene for the t8code advection example on the hybrid hypercube.

Tested with ParaView 5.11.2 (Ubuntu package, /usr/bin/pvpython). Run it with a clean
library path, otherwise pvpython picks up libraries from the module system:

  env -u LD_LIBRARY_PATH -u PYTHONPATH pvpython advect_scene.py state  <data_dir> <out.pvsm>
  env -u LD_LIBRARY_PATH -u PYTHONPATH pvpython advect_scene.py render <data_dir> <out_dir> <first> <last> [stride] [--raytrace]

'state' writes a ParaView state file for the GUI. 'render' writes one PNG per time step
(frame_NNN.png) for the steps first, first+stride, ... up to last (inclusive). Several render processes with disjoint
step ranges can run at the same time, see make_video.sh.
"""
import glob
import os
import re
import sys

from paraview.simple import *

# Scene parameters
RESOLUTION = [1080, 1350]
# Cutting plane, normal (0,1,1). In this case (run e8u3l2r5c01t1a10v50) the sphere center stays at
# y+z = 1.18..1.24, so the half sphere sits on the cut face for the whole run.
PLANE_ORIGIN = [0.5, 0.605, 0.605]
PLANE_NORMAL = [0.0, 1.0, 1.0]
# Uniform grid for the interface contour, covers the sphere path.
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
CAMERA_POSITION = [2.50, 2.39, 3.02]
CAMERA_FOCAL_POINT = [0.50, 0.50, 0.47]
CAMERA_VIEW_UP = [0.0, 0.0, 1.0]
CAMERA_VIEW_ANGLE = 30.0


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


def main():
  mode, data_dir = sys.argv[1], sys.argv[2]
  files = data_files(data_dir)
  raytrace = "--raytrace" in sys.argv
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
    SaveScreenshot(os.path.join(out_dir, "frame_%03d.png" % step), view,
                   ImageResolution=RESOLUTION, CompressionLevel="3")
    print("frame %d done" % step, flush=True)


if __name__ == "__main__":
  main()
