###############################################################################
#                                                                             #
#   t8code christmas card simulation                                          #
#   This simulation reads a Gmsh .msh file containing a christmas tree        #
#   and runs a Trixi.jl simulation of a 5 m/s wind around it.                 #
#   During the simulation, the mesh is deformed to multiple OpenCASCADE       #
#   .brep files of the same but deformed christmas tree. In the end it        #
#   looks like a christmas tree rocking in the wind.                          #
#   This simulation script is based on the Trixi.jl example                   #
#   elixir_euler_NACA0012airfoil_mach085                                      #
#                                                                             #
###############################################################################

using OrdinaryDiffEqSSPRK
using Trixi

###############################################################################
# semidiscretization of the isothermal Euler equations

# Sound waves do not matter for a wind of 5 m/s, but resolving them would limit the time
# step. Thus, the air is weakly compressible: an isothermal gas whose speed of sound is only
# ten times the wind speed. This keeps the density practically constant, like in real air.
speed_of_sound() = 50.0 # m/s
equations = PolytropicEulerEquations2D(1.0, speed_of_sound()^2)

# Air flowing with 5 m/s in x-direction
rho_inf() = 1.225 # kg/m^3
u_inf() = 5.0 # m/s

@inline function initial_condition(x, t, equations)
    prim = SVector(rho_inf(), u_inf(), 0.0)
    return prim2cons(prim, equations)
end

# Slip wall: the velocity at the tree is mirrored, so that its normal component vanishes
@inline function boundary_condition_slip_wall_tree(u_inner, normal_direction, x, t,
                                                   surface_flux_function, equations)
    rho, rho_v1, rho_v2 = u_inner
    rho_v_normal = (rho_v1 * normal_direction[1] + rho_v2 * normal_direction[2]) /
                   (normal_direction[1]^2 + normal_direction[2]^2)
    u_mirror = SVector(rho, rho_v1 - 2 * rho_v_normal * normal_direction[1],
                       rho_v2 - 2 * rho_v_normal * normal_direction[2])
    return surface_flux_function(u_inner, u_mirror, normal_direction, equations)
end

# The shock capturing keeps the simulation stable at the sharp corners of the tree, the star,
# and the baubles
basis = LobattoLegendreBasis(2)
indicator_sc = IndicatorHennemannGassner(equations, basis, alpha_max = 0.5, alpha_min = 0.001,
                                         alpha_smooth = true, variable = density)
volume_integral = VolumeIntegralShockCapturingHG(indicator_sc;
                                                 volume_flux_dg = flux_winters_etal,
                                                 volume_flux_fv = flux_lax_friedrichs)
solver = DGSEM(basis, flux_lax_friedrichs, volume_integral)

# The geometry (created by christmas_tree_brep.py, see run.sh) is in geometry/: the mesh
# christmas_tree_0000.msh of the tree in its first position and the CAD geometry
# christmas_tree_0000.brep, christmas_tree_0001.brep, ... of all its positions. The
# boundary of the mesh is taken from christmas_tree_0000.brep. The AMR refines up to two
# levels above this initial refinement level.
geometry_folder = joinpath(@__DIR__, "geometry")
initial_refinement_level = 0
mesh = T8codeMesh(joinpath(geometry_folder, "christmas_tree_0000.msh"), 2; polydeg = 2,
                  initial_refinement_level = initial_refinement_level,
                  use_cad_geometry = true)

# Boundary names are the physical groups of the msh file: the tunnel (wall) is a
# free stream, the christmas tree (slip) is a slip wall
boundary_conditions = (; wall = BoundaryConditionDirichlet(initial_condition),
                       slip = boundary_condition_slip_wall_tree)

semi = SemidiscretizationHyperbolic(mesh, equations, initial_condition, solver;
                                    boundary_conditions = boundary_conditions)

###############################################################################
# ODE solvers

# The 3 m high tree rocks with 1 Hz. The .brep files cover 1.5 periods of the rocking with
# 256 frames per period, so the deformation interval 1 / 256 s and all times below are exact
# binary fractions. The gif shows one period with 32 frames.
bending_frequency = 1.0 # Hz
period = 1 / bending_frequency
frames_per_period = 256
dt_deformation = period / frames_per_period
gif_frames_per_period = 32
dt_gif_frame = period / gif_frames_per_period

# The simulation has three stages:
# 1. t in [0, t_start]: the flow around the resting tree develops. The resting tree is
#    in its first position, i.e., the one of the mesh. t_start is long enough that the
#    pressure waves of the impulsive start have left the part of the domain shown in the gif:
#    in a square of 4.5 m around the tree, the mean deviation of the density from the free
#    stream drops within 0.3 s to a level at which it stays.
# 2. t in [t_start, t_gif]: the tree rocks for half a period, so that the flow in the
#    gif (in particular the wake) follows the rocking.
# 3. t in [t_gif, t_gif + period]: the tree rocks for one more period. Only this stage is
#    saved, one frame every dt_gif_frame. Since the motion is periodic, the gif loops
#    seamlessly from the last frame back to the first.
t_start = 16 * dt_gif_frame # 0.5 s
t_gif = t_start + period / 2
tspan = (0.0, t_gif + period)
ode = semidiscretize(semi, tspan)

# Callbacks

summary_callback = SummaryCallback()

analysis_callback = AnalysisCallback(semi, interval = 1000)

# Save the frames of stage 3: the PeriodicCallback stops the time integration at
# t_gif + k * dt_gif_frame. Its final stop at t_gif + period is not saved, since it would be
# the same frame as the first one.
save_solution = SaveSolutionCallback(dt = dt_gif_frame,
                                     save_initial_solution = false,
                                     save_final_solution = false,
                                     solution_variables = cons2prim)
save_solution = Trixi.PeriodicCallback(save_solution.affect!.affect!, dt_gif_frame;
                                       phase = t_gif, save_positions = (false, false),
                                       initialize = Trixi.initialize_save_cb!)

# The density hardly varies, so the AMR refines where the velocity deviates from the free
# stream, i.e., around the tree and in its wake, which follow the rocking tree.
@inline function velocity_deviation(u, equations)
    rho, rho_v1, rho_v2 = u
    return sqrt((rho_v1 / rho - u_inf())^2 + (rho_v2 / rho)^2)
end
amr_indicator = IndicatorMax(semi, variable = velocity_deviation)
amr_controller = ControllerThreeLevel(semi, amr_indicator,
                                      base_level = initial_refinement_level,
                                      med_level = initial_refinement_level + 1,
                                      med_threshold = 0.5 * u_inf(),
                                      max_level = initial_refinement_level + 2,
                                      max_threshold = 1.0 * u_inf())
amr_callback = AMRCallback(semi, amr_controller,
                           interval = 100,
                           adapt_initial_condition = true,
                           adapt_initial_condition_only_refine = true)

# Deform the mesh to christmas_tree_0000.brep, christmas_tree_0001.brep, ... one after
# another, starting at t_start. The globally supported thin plate splines (tps) move the
# inner vertices smoothly along with the tree.
mesh_deformation_callback = MeshDeformationCallback(brep_folder = geometry_folder,
                                                    t_start = t_start,
                                                    dt = dt_deformation,
                                                    rbf_type = :tps)

stepsize_callback = StepsizeCallback(cfl = 0.8)

# The mesh is deformed before the solution is saved, so each solution file shows the
# geometry of its time
callbacks = CallbackSet(summary_callback, analysis_callback, mesh_deformation_callback,
                        save_solution, amr_callback, stepsize_callback)

###############################################################################
# run the simulation
sol = solve(ode, SSPRK54(thread = Trixi.Threaded());
            dt = 1, # solve needs some value here but it will be overwritten by the stepsize_callback
            maxiters = typemax(Int), # the simulation needs many time steps
            save_everystep = false, callback = callbacks);
