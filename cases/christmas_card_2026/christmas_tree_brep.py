#!/usr/bin/env python3
"""Christmas tree rocking in the wind, as the negative of the tree in a wind tunnel.

Writes a series of BREP files <prefix>_0000.brep, <prefix>_0001.brep, ... Each file holds the
fluid domain of a 2D wind tunnel with a Christmas tree
cut out of it: tiered branches, a trunk standing on the tunnel floor, a star on top and
baubles hanging from the branch tips. The wind blows in +x direction. The tree bends and rocks,
each bauble swings in its own rhythm. The frames cover the given number of periods.

All frames have the same topology and every curve keeps its parametrization, so a mesh of
frame 0 can be morphed onto the other frames. Frame 0 is also meshed (<prefix>_0000.msh).

Requires the gmsh Python API (pip install gmsh).
"""

import argparse
import math
import os
import sys

import gmsh

occ = gmsh.model.occ

# Left half of the tree outline in rest position, from the tree top down to the trunk base.
# Each entry is the control polygon of a cubic Bezier curve; the right half is mirrored.
# The tree is 1 high and stands on the tunnel floor y = 0. The trunk pokes a bit below the
# floor, so that cutting it out of the tunnel does not depend on coincident edges.
TREE_LEFT_HALF = [
  [(0.0, 1.0), (-0.04, 0.9), (-0.22, 0.8), (-0.3, 0.71)],         # top tier, upper edge
  [(-0.3, 0.71), (-0.23, 0.715), (-0.15, 0.73), (-0.085, 0.76)],   # top tier, lower edge
  [(-0.085, 0.76), (-0.11, 0.62), (-0.3, 0.54), (-0.37, 0.44)],    # middle tier, upper edge
  [(-0.37, 0.44), (-0.3, 0.445), (-0.21, 0.465), (-0.14, 0.49)],   # middle tier, lower edge
  [(-0.14, 0.49), (-0.19, 0.35), (-0.38, 0.27), (-0.45, 0.17)],    # bottom tier, upper edge
  [(-0.45, 0.17), (-0.33, 0.17), (-0.21, 0.17), (-0.09, 0.17)],    # bottom tier, lower edge
  [(-0.09, 0.17), (-0.09, 0.09), (-0.09, 0.01), (-0.09, -0.07)],   # trunk
  [(-0.09, -0.07), (-0.06, -0.07), (-0.03, -0.07), (0.0, -0.07)],  # trunk base, below the floor
]

STAR_CENTER = 1.06
STAR_OUTER_RADIUS = 0.12
STAR_INNER_RADIUS = 0.065
# The star sits on a stem reaching down into the tree. Its vertical sides meet the star and the
# tree at much wider angles than the slanted tree top, which is easier to mesh. Heights are
# relative to the star center.
STEM_HALF_WIDTH = 0.03
STEM_BOTTOM = -0.28
STEM_TOP = -0.02

# Baubles on the left half, mirrored to the right: the tier (0 = top) whose tip they hang from,
# the horizontal distance of the string from the tip and the string length to the ball center.
# Share of the lean that comes from an even bend along the whole tree. The rest grows towards the
# top. Without it, only the upper part of the tree would move and the trunk would stay rigid.
TRUNK_FLEX = 0.3

BAUBLES_LEFT_HALF = [(0, 0.045, 0.09), (1, 0.045, 0.09), (2, 0.045, 0.09)]
# Every bauble swings in its own rhythm: (frequency, direction) relative to the rocking of the
# tree, in the order of baubles(). All baubles are at their mean angle in frame 0, the meshed
# one, so that no frame moves them further than the swing amplitude away from it. The top left
# bauble swings against the tree, otherwise it is pushed into the middle tier when the tree leans.
BAUBLE_RHYTHMS = [(1, -1), (2, 1), (1, 1), (2, -1), (1, -1), (2, 1)]
STRING_WIDTH = 0.02
BALL_RADIUS = 0.03


def tree_outline():
    """Control polygons of the closed tree outline, counterclockwise."""
    right_half = [[(-x, y) for x, y in reversed(polygon)] for polygon in reversed(TREE_LEFT_HALF)]
    return TREE_LEFT_HALF + right_half


def bezier(polygon, t):
    """Point at parameter t of the Bezier curve with the given control polygon."""
    while len(polygon) > 1:
        polygon = [((1 - t) * x0 + t * x1, (1 - t) * y0 + t * y1) for (x0, y0), (x1, y1) in zip(polygon, polygon[1:])]
    return polygon[0]


def height_at(polygon, x):
    """Height of a Bezier curve that is monotonic in x at the position x."""
    lower, upper = 0.0, 1.0
    increasing = polygon[-1][0] > polygon[0][0]
    for _ in range(60):
        middle = (lower + upper) / 2
        if (bezier(polygon, middle)[0] < x) == increasing:
            lower = middle
        else:
            upper = middle
    return bezier(polygon, lower)[1]


def baubles():
    """(anchor, string length) of all baubles; left half first, then the mirrored right half.

    The string is fixed halfway between the upper and lower edge of the branch."""
    left_half = []
    for tier, distance, length in BAUBLES_LEFT_HALF:
        upper_edge, lower_edge = TREE_LEFT_HALF[2 * tier], TREE_LEFT_HALF[2 * tier + 1]
        x = upper_edge[-1][0] + distance
        left_half.append(((x, (height_at(upper_edge, x) + height_at(lower_edge, x)) / 2), length))
    return left_half + [((-x, y), length) for (x, y), length in left_half]


def tangent_angle(height, lean):
    """Clockwise angle of the bent tree axis against the vertical at the given height.

    The tree is a beam clamped at the floor. Its curvature is partly constant (TRUNK_FLEX) and
    partly growing linearly with the height, and the angle reaches `lean` at the tree top."""
    height = max(height, 0.0)
    return lean * (TRUNK_FLEX * height + (1 - TRUNK_FLEX) * height**2)


def bend(x, y, lean):
    """Position of the rest position point (x, y) of the tree in the wind.

    The point keeps its height along the (inextensible) tree axis and its distance to it."""
    if y <= 0.0:
        return x, y
    # Simpson integration of the axis tangent from the floor to y.
    num_intervals = 64
    step = y / num_intervals
    axis_x = axis_y = 0.0
    for i in range(num_intervals + 1):
        weight = 1 if i in (0, num_intervals) else 4 if i % 2 else 2
        angle = tangent_angle(i * step, lean)
        axis_x += weight * math.sin(angle)
        axis_y += weight * math.cos(angle)
    axis_x *= step / 3
    axis_y *= step / 3
    angle = tangent_angle(y, lean)
    return axis_x + x * math.cos(angle), axis_y - x * math.sin(angle)


def add_tree(lean):
    """Face of the bent tree body and trunk."""
    outline = tree_outline()
    first = occ.addPoint(*bend(*outline[0][0], lean), 0)
    start = first
    curves = []
    for index, polygon in enumerate(outline):
        inner = [occ.addPoint(*bend(x, y, lean), 0) for x, y in polygon[1:-1]]
        end = first if index == len(outline) - 1 else occ.addPoint(*bend(*polygon[-1], lean), 0)
        curves.append(occ.addBSpline([start] + inner + [end]))
        # The inner control points are not on the curve and would end up as loose vertices.
        occ.remove([(0, point) for point in inner])
        start = end
    return occ.addPlaneSurface([occ.addCurveLoop(curves)])


def add_star(lean):
    """Five-pointed star on a stem on the tree top, moving rigidly with it.

    Like the baubles, it is built at the origin and then moved, so that its curves keep the same
    parametrization in all frames."""
    points = []
    for corner in range(10):
        radius = STAR_OUTER_RADIUS if corner % 2 == 0 else STAR_INNER_RADIUS
        angle = math.pi / 2 + corner * math.pi / 5
        points.append(occ.addPoint(radius * math.cos(angle), radius * math.sin(angle), 0))
    lines = [occ.addLine(points[corner], points[(corner + 1) % 10]) for corner in range(10)]
    star = occ.addPlaneSurface([occ.addCurveLoop(lines)])
    stem = occ.addRectangle(-STEM_HALF_WIDTH, STEM_BOTTOM, 0, 2 * STEM_HALF_WIDTH, STEM_TOP - STEM_BOTTOM)
    parts = [(2, star), (2, stem)]
    occ.rotate(parts, 0, 0, 0, 0, 0, 1, -tangent_angle(STAR_CENTER, lean))
    occ.translate(parts, *bend(0.0, STAR_CENTER, lean), 0)
    return parts


def add_bauble(anchor, length, swing):
    """String and ball of a bauble hanging from `anchor`, swung by `swing` out of the vertical.

    Both are built hanging straight down from the origin and then moved rigidly, so their curves
    keep the same parametrization in all frames. The seam of the ball is at its bottom."""
    string = occ.addRectangle(-STRING_WIDTH / 2, -length, 0, STRING_WIDTH, length)
    ball = occ.addDisk(0, -length, 0, BALL_RADIUS, BALL_RADIUS, zAxis=[0, 0, 1], xAxis=[0, -1, 0])
    parts = [(2, string), (2, ball)]
    occ.rotate(parts, 0, 0, 0, 0, 0, 1, swing)
    occ.translate(parts, anchor[0], anchor[1], 0)
    return string, ball


def build_frame(lean, swings, args):
    """Build the fluid domain of one frame in the gmsh model. Return the smallest gap between a
    ball and the tree or the floor."""
    tree = add_tree(lean)
    balls = []
    obstacles = [(2, tree)] + add_star(lean)
    for (anchor, length), swing in zip(baubles(), swings):
        string, ball = add_bauble(bend(*anchor, lean), length, swing)
        balls.append(ball)
        obstacles += [(2, string), (2, ball)]
    min_gap = min(min(occ.getDistance(2, ball, 2, tree)[0], occ.getBoundingBox(2, ball)[1]) for ball in balls)

    x_min, x_max, y_max = args.tunnel
    tunnel = occ.addRectangle(x_min, 0, 0, x_max - x_min, y_max)
    fluid, _ = occ.cut([(2, tunnel)], obstacles)
    if len(fluid) != 1:
        sys.exit(f"Expected one connected fluid domain, got {len(fluid)} pieces. Is the tree outside the tunnel?")
    # Everything above is built with a tree that is 1 high without the star; scale it to meters.
    occ.dilate(fluid, 0, 0, 0, scale(args), scale(args), scale(args))
    occ.synchronize()
    return min_gap * scale(args)


def scale(args):
    """Length in meters of one unit of the geometry, i.e., of the height of the tree without the star."""
    return args.height / (STAR_CENTER + STAR_OUTER_RADIUS)


def topology_signature():
    """Entity tags and types of the current model, which have to agree between all frames."""
    return [(dim, tag, gmsh.model.getType(dim, tag)) for dim in range(4) for _, tag in gmsh.model.getEntities(dim)]


def mesh_frame(msh_file, args):
    """Quadrilateral mesh of the loaded BREP geometry, refined towards the tree."""
    x_min, x_max, y_max = (scale(args) * value for value in args.tunnel)
    walls = [(0, x_min), (0, x_max), (1, 0.0), (1, y_max)]
    tolerance = 1e-6

    def on_tunnel_wall(dim, tag):
        box = gmsh.model.getBoundingBox(dim, tag)
        return any(abs(box[axis] - value) < tolerance and abs(box[axis + 3] - value) < tolerance for axis, value in walls)

    boundary = gmsh.model.getEntities(1)
    wall_entities = [tag for dim, tag in boundary if on_tunnel_wall(dim, tag)]
    tree_entities = [tag for dim, tag in boundary if not on_tunnel_wall(dim, tag)]
    # Boundary conditions. Once there are physical groups, only their elements are saved, so the
    # fluid domain needs one as well.
    gmsh.model.addPhysicalGroup(1, wall_entities, name="wall")
    gmsh.model.addPhysicalGroup(1, tree_entities, name="slip")
    gmsh.model.addPhysicalGroup(2, [tag for _, tag in gmsh.model.getEntities(2)], name="fluid")

    fields = gmsh.model.mesh.field
    distance = fields.add("Distance")
    fields.setNumbers(distance, "CurvesList", tree_entities)
    fields.setNumber(distance, "Sampling", 200)
    threshold = fields.add("Threshold")
    fields.setNumber(threshold, "InField", distance)
    fields.setNumber(threshold, "SizeMin", scale(args) * (args.mesh_size_tree or args.mesh_size / 10))
    fields.setNumber(threshold, "SizeMax", scale(args) * args.mesh_size)
    fields.setNumber(threshold, "DistMin", scale(args) * 0.02)
    fields.setNumber(threshold, "DistMax", scale(args) * 0.5)
    fields.setAsBackgroundMesh(threshold)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    # Quadrilaterals only, from the quasi-structured quad algorithm. It copes better with the
    # sharp tips of the star and the branches than recombination and subdivision.
    gmsh.option.setNumber("Mesh.Algorithm", 11)
    gmsh.model.mesh.generate(2)
    # Store the parametric coordinates of the boundary nodes on the CAD curves/surfaces.
    gmsh.option.setNumber("Mesh.SaveParametric", 1)
    gmsh.option.setNumber("Mesh.MshFileVersion", 4.1)
    gmsh.write(msh_file)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-n", "--frames", type=int, default=24, help="number of frames per period (default: 24)")
    parser.add_argument("--periods", type=float, default=1, help="number of periods (default: 1)")
    parser.add_argument("-o", "--output-dir", default=".", help="directory for the output files")
    parser.add_argument("--prefix", default="christmas_tree", help="file prefix (default: christmas_tree)")
    parser.add_argument("--lean", type=float, default=7.0, help="mean lean of the tree top in degrees (default: 7)")
    parser.add_argument("--lean-amplitude", type=float, default=9.0,
                        help="amplitude of the rocking in degrees (default: 9)")
    parser.add_argument("--swing", type=float, default=0.0,
                        help="mean angle of the bauble strings against the vertical in degrees (default: 0)")
    parser.add_argument("--swing-amplitude", type=float, default=12.0,
                        help="amplitude of the bauble swinging in degrees (default: 12)")
    parser.add_argument("--height", type=float, default=STAR_CENTER + STAR_OUTER_RADIUS,
                        help="height of the tree including the star in m; all other lengths are given relative to the "
                        "height of the tree without the star (default: 1.18, i.e., 1 m without the star)")
    parser.add_argument("--tunnel", type=float, nargs=3, default=[-2.0, 4.0, 2.0], metavar=("XMIN", "XMAX", "YMAX"),
                        help="wind tunnel extent; the floor is at y = 0 and the tree is 1 high (default: -2 4 2)")
    parser.add_argument("--mesh-size", type=float, default=1.0,
                        help="far field mesh size of the mesh of frame 0 (default: 1)")
    parser.add_argument("--mesh-size-tree", type=float, default=0.0,
                        help="mesh size at the tree (default: mesh size / 10)")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    reference_signature = None
    for frame in range(round(args.frames * args.periods)):
        phase = 2 * math.pi * frame / args.frames
        lean = math.radians(args.lean + args.lean_amplitude * math.sin(phase))
        swings = [
            math.radians(args.swing + args.swing_amplitude * direction * math.sin(frequency * phase))
            for frequency, direction in BAUBLE_RHYTHMS
        ]

        gmsh.clear()
        min_gap = build_frame(lean, swings, args)
        prefix = os.path.join(args.output_dir, f"{args.prefix}_{frame:04d}")
        gmsh.write(prefix + ".brep")

        # Reload the BREP file, so that gmsh uses the entity numbering of the file, which is what other tools reading it see.
        gmsh.clear()
        gmsh.merge(prefix + ".brep")
        signature = topology_signature()
        if reference_signature is None:
            reference_signature = signature
        elif signature != reference_signature:
            sys.exit(f"{prefix}.brep: topology differs from frame 0, the frames cannot be used for mesh deformation. "
                     "Probably a bauble touches the tree; reduce --swing/--swing-amplitude or --lean-amplitude.")
        if frame == 0:
            mesh_frame(prefix + ".msh", args)
        print(f"{prefix}.brep: lean {math.degrees(lean):5.1f} deg, smallest gap bauble-tree/floor {min_gap:.3f}")

    gmsh.finalize()


if __name__ == "__main__":
    main()
