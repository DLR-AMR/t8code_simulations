# t8code_simulations
Easily reproduce t8code simulations and usecases

**NOTE: THIS REPOSITORY IS STILL WORK IN PROGRESS**

## "Protocol" of inital discussion

We agreed on the follwoing main points:

- The key objectives are:
  1. It should be **easy to conrtibute** by adding a new example case;
  2. It should be **easy to reproduce** the results of an existing example.
- We use the memilio-simulations repo as inspiration and orientation.
- Our reference system is the AMR Teamserver. Anything beyond that is nice-to-have, but we do not guarantee it will work on other systems.
- One top-level CMake script will trigger the specific example, chosen via CMake options.
- To handle the exact versions of t8code and external libraries, such as Trixi, we rely on CMake FetchContent. For this we provide a unified framework, such that a contributor can easily define which commit hash of which repository is used.
- For the main workflow of each example (typically configuring, building, running the simulation and perfomring some post-processing), we do not prescribe a fixed structure to maximize flexibility; instead, we just provide one main script, say `run_example.sh`, per folder that produces the results.
- It will probably be useful to allow for some "revisions" of the cases, i.e., to update the commit hashes to newer ones once they are ensured to work properly, **WITHOUT** overwriting the original case, as it might be coupled to some publication.
- For some software packages involved, e.g., Paraview, we can simply state the version used and/or the Teamserver module, without using FetchContent etc.
- Note on keeping the folders up-to-date: For now, we explicitly refrain from using commit hashes like "latest" or branch names, because ensuring the examples always stay functional for the current branch is only possible through a dedicated automated testing procedure we do not want to implement as of yet.
