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

# The geometry of the boundary is taken from christmas_tree_0000.brep. The AMR refines
# up to two levels above this initial refinement level.
initial_refinement_level = 0
mesh = T8codeMesh("christmas_tree_0000.msh", 2; polydeg = 2,
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

# The 3 m high tree rocks with 1 Hz.
# The .brep files cover 1.5 periods of the rocking with 256 frames per period, so the
# deformation interval 1 / 256 s and all output times below are exact binary fractions. The
# deformation starts at t_start, once the flow around the resting tree has converged, and
# ends after the 1.5 periods, of which a full period can be looped.
bending_frequency = 1.0 # Hz
frames_per_period = 256
dt_deformation = 1 / (bending_frequency * frames_per_period)
t_start = 1.2
tspan = (0.0, t_start + 1.5 / bending_frequency)
ode = semidiscretize(semi, tspan)

# Callbacks

summary_callback = SummaryCallback()

analysis_callback = AnalysisCallback(semi, interval = 100)

# A frame every eigth deformation gives 32 frames per period of the rocking
save_solution = SaveSolutionCallback(dt = 8 * dt_deformation,
                                     save_initial_solution = true,
                                     save_final_solution = true,
                                     solution_variables = cons2prim)

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
# another, starting at t_start. The globally supported thin plate splines (tps) keep the
# elements next to the moving tree valid.
mesh_deformation_callback = MeshDeformationCallback(brep_folder = ".",
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
            dt = 1.0, # solve needs some value here but it will be overwritten by the stepsize_callback
            maxiters = typemax(Int), # the simulation needs many time steps
            ode_default_options()..., callback = callbacks);
