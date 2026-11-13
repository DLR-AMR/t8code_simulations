#!/usr/bin/env python3
"""Christmas tree rocking in the wind, as the negative of the tree in a wind tunnel.

Writes a series of BREP files <prefix>_0000.brep, <prefix>_0001.brep, ... Each file holds the
fluid domain of a 2D wind tunnel with a Christmas tree cut out of it: tiered branches, a trunk
standing on the tunnel floor, a star on a stem on top and baubles hanging from the branch tips.
The wind blows in +x direction. The tree bends and rocks, each bauble swings in its own rhythm.
The frames cover the given number of periods.

A mesh of frame 0 (<prefix>_0000.msh) is morphed onto the other frames by keeping the curve
parameters of its boundary nodes. Hence, all frames have the same topology and every curve
has the same parameter range in all frames. This is needed for the current development state of
t8codes mesh deformation module, but will not be a requirement in the future anymore.
Therefore, this script is overly complicated and could be shortened significantly with future
t8code versions.

Requires the gmsh Python API (see environment.txt).
"""

import argparse
import math
import os
import sys

import gmsh

occ = gmsh.model.occ

# Left half of the tree outline in rest position, from the tree top down to the floor.
# Each entry is the control polygon of a cubic Bezier curve; the right half is mirrored.
# The tree is 1 high and stands on the tunnel floor y = 0.
TREE_LEFT_HALF = [
  [(0.0, 1.0), (-0.04, 0.9), (-0.22, 0.8), (-0.3, 0.71)],         # top tier, upper edge
  [(-0.3, 0.71), (-0.23, 0.715), (-0.15, 0.73), (-0.085, 0.76)],   # top tier, lower edge
  [(-0.085, 0.76), (-0.11, 0.62), (-0.3, 0.54), (-0.37, 0.44)],    # middle tier, upper edge
  [(-0.37, 0.44), (-0.3, 0.445), (-0.21, 0.465), (-0.14, 0.49)],   # middle tier, lower edge
  [(-0.14, 0.49), (-0.19, 0.35), (-0.38, 0.27), (-0.45, 0.17)],    # bottom tier, upper edge
  [(-0.45, 0.17), (-0.33, 0.17), (-0.21, 0.17), (-0.09, 0.17)],    # bottom tier, lower edge
  [(-0.09, 0.17), (-0.09, 0.115), (-0.09, 0.055), (-0.09, 0.0)],   # trunk
]

STAR_CENTER = 1.06
STAR_OUTER_RADIUS = 0.12
STAR_INNER_RADIUS = 0.065
# The star sits on a stem reaching down to the tree top. Its vertical sides meet the star and
# the tree at much wider angles than the slanted tree top, which is easier to mesh.
STEM_HALF_WIDTH = 0.03

# Share of the lean that comes from an even bend along the whole tree. The rest grows towards the
# top. Without it, only the upper part of the tree would move and the trunk would stay rigid.
TRUNK_FLEX = 0.3

# Baubles on the left half, mirrored to the right: the tier (0 = top) whose tip they hang from,
# the horizontal distance of the string from the tip and the string length to the ball center.
# The string hangs from a pivot halfway between the upper and lower edge of the branch and is
# attached to the lower edge.
BAUBLES_LEFT_HALF = [(0, 0.045, 0.09), (1, 0.045, 0.09), (2, 0.045, 0.09)]
# Every bauble swings in its own rhythm: (frequency, direction) relative to the rocking of the
# tree, in the order of baubles(). All baubles are at their mean angle in frame 0, the meshed
# one, so that no frame moves them further than the swing amplitude away from it. The top left
# bauble swings against the tree, otherwise it is pushed into the middle tier when the tree leans.
BAUBLE_RHYTHMS = [(1, -1), (2, 1), (1, 1), (2, -1), (1, -1), (2, 1)]
STRING_WIDTH = 0.02
BALL_RADIUS = 0.03


def bezier(polygon, t):
    """Point at parameter t of the Bezier curve with the given control polygon."""
    while len(polygon) > 1:
        polygon = [((1 - t) * x0 + t * x1, (1 - t) * y0 + t * y1) for (x0, y0), (x1, y1) in zip(polygon, polygon[1:])]
    return polygon[0]


def split_bezier(polygon, t):
    """Control polygons of the two pieces of a Bezier curve split at parameter t."""
    first, second = [polygon[0]], [polygon[-1]]
    while len(polygon) > 1:
        polygon = [((1 - t) * x0 + t * x1, (1 - t) * y0 + t * y1) for (x0, y0), (x1, y1) in zip(polygon, polygon[1:])]
        first.append(polygon[0])
        second.append(polygon[-1])
    return first, second[::-1]


def parameter_at(polygon, x):
    """Parameter of a Bezier curve that is monotonic in x at the position x."""
    lower, upper = 0.0, 1.0
    increasing = polygon[-1][0] > polygon[0][0]
    for _ in range(60):
        middle = (lower + upper) / 2
        if (bezier(polygon, middle)[0] < x) == increasing:
            lower = middle
        else:
            upper = middle
    return lower


def baubles():
    """(pivot, string length) of all baubles; left half first, then the mirrored right half."""
    left_half = []
    for tier, distance, length in BAUBLES_LEFT_HALF:
        upper_edge, lower_edge = TREE_LEFT_HALF[2 * tier], TREE_LEFT_HALF[2 * tier + 1]
        x = upper_edge[-1][0] + distance
        y_upper = bezier(upper_edge, parameter_at(upper_edge, x))[1]
        y_lower = bezier(lower_edge, parameter_at(lower_edge, x))[1]
        left_half.append(((x, (y_upper + y_lower) / 2), length))
    return left_half + [((-x, y), length) for (x, y), length in left_half]


def star_corner(corner):
    """Corner of the star in its own frame, counterclockwise from the top (corner 0)."""
    radius = STAR_OUTER_RADIUS if corner % 2 == 0 else STAR_INNER_RADIUS
    angle = math.pi / 2 + corner * math.pi / 5
    # Rounded, so that the top corner is exactly on the axis and equals its mirror image.
    return round(radius * math.cos(angle), 12) + 0.0, round(radius * math.sin(angle), 12) + 0.0


# A point of the outline is described in the frame of the part it is fixed to:
#   ("tree", x, y):       rest position on the tree, moved by bend()
#   ("star", x, y):       relative to the star center, moved rigidly with the star
#   ("bauble", i, x, y):  relative to the pivot of bauble i, moved rigidly with it
#   ("fixed", x, y):      not moving
# A curve is (kind, [points], weights). A "bezier" curve, given by its control points, is
# parametrized by [0, 1] in all frames. A straight "bezier" curve with two points can connect
# two parts that move differently, which changes its length. A "line" is parametrized by its
# arc length, so it has to belong to a rigid part. A "rational" curve is a rational quadratic
# Bezier curve with the given weights, e.g., a circular arc. It is also parametrized by [0, 1],
# in contrast to the circle arcs of OpenCASCADE, whose parameter is the angle with respect to
# the x-axis, which changes when a rigid part rotates.


def circular_arc(part, center, radius, start_angle, end_angle):
    """Circular arc (less than pi) of a rigid part, counterclockwise from the start to the end angle."""
    def point(angle, distance):
        return (*part, round(center[0] + distance * math.cos(angle), 12) + 0.0,
                round(center[1] + distance * math.sin(angle), 12) + 0.0)
    half_angle = (end_angle - start_angle) / 2
    middle = point(start_angle + half_angle, radius / math.cos(half_angle))
    return ("rational", [point(start_angle, radius), middle, point(end_angle, radius)], [1.0, math.cos(half_angle), 1.0])


def left_half_outline():
    """Curves of the left half of the outline in rest position, from the top of the star down
    to the trunk on the floor."""
    def tree_curve(polygon):
        return ("bezier", [("tree", *point) for point in polygon], None)

    curves = []
    # Star from its top to the stem, counterclockwise
    for corner in range(4):
        curves.append(("line", [("star", *star_corner(corner)), ("star", *star_corner(corner + 1))], None))
    (x4, y4), (x5, y5) = star_corner(4), star_corner(5)
    stem_on_star = ("star", -STEM_HALF_WIDTH, y4 + (y5 - y4) * (-STEM_HALF_WIDTH - x4) / (x5 - x4))
    curves.append(("line", [("star", x4, y4), stem_on_star], None))
    # Stem down to the tree top; the tip of the tree top is hidden in it
    top_edge = TREE_LEFT_HALF[0]
    _, top_edge = split_bezier(top_edge, parameter_at(top_edge, -STEM_HALF_WIDTH))
    curves.append(("bezier", [stem_on_star, ("tree", *top_edge[0])], None))
    # Tiers with the baubles hanging from the lower edges
    for tier in range(3):
        curves.append(tree_curve(top_edge if tier == 0 else TREE_LEFT_HALF[2 * tier]))
        lower_edge = TREE_LEFT_HALF[2 * tier + 1]
        (pivot_x, _), length = baubles()[tier]
        half_width = STRING_WIDTH / 2
        # The piece of the lower edge between the two ends of the string is hidden in it.
        to_string, lower_edge = split_bezier(lower_edge, parameter_at(lower_edge, pivot_x - half_width))
        curves.append(tree_curve(to_string))
        string_on_tree = [("tree", *lower_edge[0])]
        _, lower_edge = split_bezier(lower_edge, parameter_at(lower_edge, pivot_x + half_width))
        string_on_tree.append(("tree", *lower_edge[0]))
        # The string is attached to the lower edge and meets the ball on its circle, which is
        # split at its bottom.
        string_angle = math.asin(half_width / BALL_RADIUS)
        bauble = ("bauble", tier)
        arcs = [circular_arc(bauble, (0.0, -length), BALL_RADIUS, math.pi / 2 + string_angle, 1.5 * math.pi),
                circular_arc(bauble, (0.0, -length), BALL_RADIUS, 1.5 * math.pi, 2.5 * math.pi - string_angle)]
        curves += [("bezier", [string_on_tree[0], arcs[0][1][0]], None), *arcs,
                   ("bezier", [arcs[1][1][-1], string_on_tree[1]], None)]
        curves.append(tree_curve(lower_edge))
    curves.append(tree_curve(TREE_LEFT_HALF[-1]))
    return curves


def mirror_point(point):
    if point[0] == "bauble":
        return ("bauble", point[1] + len(BAUBLES_LEFT_HALF), -point[2] + 0.0, point[3])
    return (point[0], -point[1] + 0.0, point[2])


def reverse_curve(curve):
    kind, points, weights = curve
    return (kind, points[::-1], weights[::-1] if weights else None)


def mirror_curve(curve):
    """Curve mirrored at the tree axis and reversed."""
    kind, points, weights = reverse_curve(curve)
    return (kind, [mirror_point(point) for point in points], weights)


def outline():
    """Curves of the outline, from the left end of the trunk on the floor up to the top of
    the star and down to the right end of the trunk, all in this direction."""
    left_up = [reverse_curve(curve) for curve in reversed(left_half_outline())]
    right_down = [mirror_curve(curve) for curve in reversed(left_up)]
    return left_up + right_down


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


def rigid(x, y, angle, origin):
    """Point (x, y) of a rigid part rotated counterclockwise by angle and moved to origin."""
    return (origin[0] + x * math.cos(angle) - y * math.sin(angle),
            origin[1] + x * math.sin(angle) + y * math.cos(angle))


def place(point, lean, swings):
    """Position of an outline point in the frame with the given lean and bauble swings."""
    kind = point[0]
    if kind == "tree":
        return bend(point[1], point[2], lean)
    if kind == "star":
        # The star is attached to the tree axis and tilts with it.
        return rigid(point[1], point[2], -tangent_angle(STAR_CENTER, lean), bend(0.0, STAR_CENTER, lean))
    if kind == "bauble":
        pivot, _ = baubles()[point[1]]
        return rigid(point[2], point[3], swings[point[1]], bend(*pivot, lean))
    return point[1], point[2]


def build_frame(lean, swings, args):
    """Build the fluid domain of one frame in the gmsh model. Return the smallest gap between a
    ball and the rest of the tree or the floor."""
    point_tags = {}

    def point_tag(point):
        if point not in point_tags:
            point_tags[point] = occ.addPoint(*place(point, lean, swings), 0)
        return point_tags[point]

    # The inner control points are not on the curves and are removed afterwards, otherwise they
    # would end up as loose vertices.
    auxiliary = []

    def add_curve(curve):
        kind, points, weights = curve
        if kind == "line":
            return occ.addLine(point_tag(points[0]), point_tag(points[1]))
        inner = [occ.addPoint(*place(point, lean, swings), 0) for point in points[1:-1]]
        auxiliary.extend(inner)
        return occ.addBSpline([point_tag(points[0])] + inner + [point_tag(points[-1])], degree=len(points) - 1,
                              weights=weights or [])

    tree_curves = outline()
    tree_tags = [add_curve(curve) for curve in tree_curves]

    # The tunnel, whose floor is interrupted by the trunk
    x_min, x_max, y_max = args.tunnel
    trunk_left, trunk_right = tree_curves[0][1][0], tree_curves[-1][1][-1]
    corners = [("fixed", x_max, 0.0), ("fixed", x_max, y_max), ("fixed", x_min, y_max), ("fixed", x_min, 0.0)]
    tunnel_tags = [occ.addLine(point_tag(start), point_tag(end))
                   for start, end in zip([trunk_right] + corners, corners + [trunk_left])]
    fluid = occ.addPlaneSurface([occ.addCurveLoop(tree_tags + tunnel_tags)])
    occ.remove([(0, point) for point in auxiliary])

    # Smallest gap between a ball and the rest of the tree (except its own string) or the floor
    min_gap = math.inf
    for bauble in range(len(baubles())):
        own = [tag for tag, curve in zip(tree_tags, tree_curves)
               if any(point[:2] == ("bauble", bauble) for point in curve[1])]
        balls = [tag for tag, curve in zip(tree_tags, tree_curves) if curve[0] == "rational" and tag in own]
        for ball in balls:
            # Only curves near the ball can be closer than its distance to the floor.
            ball_x_min, ball_y_min, _, ball_x_max, ball_y_max, _ = occ.getBoundingBox(1, ball)
            min_gap = min(min_gap, ball_y_min)
            for other in tree_tags:
                if other in own:
                    continue
                box = occ.getBoundingBox(1, other)
                if (box[0] < ball_x_max + min_gap and box[3] > ball_x_min - min_gap
                        and box[1] < ball_y_max + min_gap and box[4] > ball_y_min - min_gap):
                    min_gap = min(min_gap, occ.getDistance(1, ball, 1, other)[0])

    # Everything above is built with a tree that is 1 high without the star; scale it to meters.
    occ.dilate([(2, fluid)], 0, 0, 0, scale(args), scale(args), scale(args))
    occ.synchronize()
    return min_gap * scale(args)


def scale(args):
    """Length in meters of one unit of the geometry, i.e., of the height of the tree without the star."""
    return args.height / (STAR_CENTER + STAR_OUTER_RADIUS)


def topology_signature():
    """Entity tags and types of the current model, which have to agree between all frames."""
    return [(dim, tag, gmsh.model.getType(dim, tag)) for dim in range(4) for _, tag in gmsh.model.getEntities(dim)]


def parametrization_signature():
    """Parameter ranges of all curves of the current model, which have to agree between all frames."""
    return [(tag, *(bound[0] for bound in gmsh.model.getParametrizationBounds(1, tag)))
            for _, tag in gmsh.model.getEntities(1)]


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
    # Store the parametric coordinates of the boundary nodes on the CAD curves.
    gmsh.option.setNumber("Mesh.SaveParametric", 1)
    gmsh.option.setNumber("Mesh.MshFileVersion", 4.1)
    gmsh.option.setNumber("Mesh.Binary", 0)
    gmsh.write(msh_file)
    strip_surface_parameters(msh_file)


def strip_surface_parameters(msh_file):
    """Remove the parametric coordinates of the nodes inside the fluid domain from an ASCII
    msh 4.1 file, keeping those of the nodes on the curves.

    t8code links a tree whose nodes all have parametric coordinates on a CAD surface to this
    surface and computes its geometry from these coordinates instead of its vertices. The mesh
    deformation (t8_cmesh_deform_to_brep) moves the vertices but keeps the parametric
    coordinates, so the inner nodes would not move at all and the elements next to the moving
    tree would be crushed. The fluid domain is plane, so its trees do not need the surface:
    without it, their geometry is the bilinear map of their vertices plus the displacement of
    their edges on the curves of the tree outline."""
    with open(msh_file) as file:
        lines = file.read().split("\n")
    start = lines.index("$Nodes")
    output = lines[:start + 2]
    line = start + 2
    for _ in range(int(lines[start + 1].split()[0])):
        dim, tag, parametric, num_nodes = (int(value) for value in lines[line].split())
        strip = parametric and dim == 2
        output.append(f"{dim} {tag} {0 if strip else parametric} {num_nodes}")
        output += lines[line + 1:line + 1 + num_nodes]  # node tags
        coordinates = lines[line + 1 + num_nodes:line + 1 + 2 * num_nodes]
        output += [" ".join(coordinate.split()[:3]) for coordinate in coordinates] if strip else coordinates
        line += 1 + 2 * num_nodes
    if lines[line] != "$EndNodes":
        sys.exit(f"{msh_file}: unexpected format of the $Nodes section")
    with open(msh_file, "w") as file:
        file.write("\n".join(output + lines[line:]))


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
    # With larger amplitudes, the right bauble of the top tier comes so close to the middle tier
    # that the morphed mesh of frame 0 gets inverted elements there.
    parser.add_argument("--swing-amplitude", type=float, default=9.0,
                        help="amplitude of the bauble swinging in degrees (default: 9)")
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
    reference_parametrization = None
    for frame in range(round(args.frames * args.periods)):
        phase = 2 * math.pi * frame / args.frames
        lean = math.radians(args.lean + args.lean_amplitude * math.sin(phase))
        swings = [
            math.radians(args.swing + args.swing_amplitude * direction * math.sin(frequency * phase))
            for frequency, direction in BAUBLE_RHYTHMS
        ]

        gmsh.clear()
        min_gap = build_frame(lean, swings, args)
        if min_gap <= 0.0:
            sys.exit(f"Frame {frame}: a bauble touches the tree; reduce --swing/--swing-amplitude or --lean-amplitude.")
        prefix = os.path.join(args.output_dir, f"{args.prefix}_{frame:04d}")
        gmsh.write(prefix + ".brep")

        # Reload the BREP file, so that gmsh uses the entity numbering of the file, which is what other tools reading it see.
        gmsh.clear()
        gmsh.merge(prefix + ".brep")
        signature = topology_signature()
        parametrization = parametrization_signature()
        if reference_signature is None:
            reference_signature = signature
            reference_parametrization = parametrization
        elif signature != reference_signature:
            sys.exit(f"{prefix}.brep: topology differs from frame 0, the frames cannot be used for mesh deformation.")
        else:
            differing = [(current, reference) for current, reference in zip(parametrization, reference_parametrization)
                         if any(abs(a - b) > 1e-9 * max(1.0, abs(b)) for a, b in zip(current, reference))]
            if differing:
                sys.exit(f"{prefix}.brep: parameter ranges of curves differ from frame 0, the frames cannot be used "
                         f"for mesh deformation: {differing} (tag, start, end)")
        if frame == 0:
            mesh_frame(prefix + ".msh", args)
        print(f"{prefix}.brep: lean {math.degrees(lean):5.1f} deg, smallest gap bauble-tree/floor {min_gap:.3f}")

    gmsh.finalize()


if __name__ == "__main__":
    main()
