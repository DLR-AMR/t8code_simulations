# t8code_simulations
Easily reproduce t8code simulations and usecases

**NOTE: THIS REPOSITORY IS STILL WORK IN PROGRESS**

The goal of this repostory is to make it very simple to reproduce the results of any t8code simulations stored here, e.g., to reproducce the results of a thesis or paper.

## Structure of this repository

The process of running any of the provided cases is orchestrated by a top-level CMake workflow. Note that it is independent from the CMake config of the cases themselves. It is primarily used to
* check the given case directory for completeness,
* automatically download the dependencies of a case via CMake FetchContent,
* and execute the case's run.sh script, which is responsible for all case-specific workflows.

## How to run an existing case

You can run an existing case via the top-level CMake script. The main argument is `-DCASE_DIR`, which should be the subfolder of a case.
For example,
```
cmake . -DCASE_DIR=./cases/hello_world
```


## Technical aspects

Our reference hardware is the AMR teamserver - An Ubuntu 24.04 system at DLR. We do not guarantee it will run on any other system, but to keep adoption simple, all teamserver-specific settings are encapsulated in a separate (case-level) script.


## Adding a new case

To add a new case, you first have to pick a name `$CASE_NAME` and then create a new folder `cases/$CASE_NAME`.
Next, set up the case by adding the following files:

- `README.md`:
  * The case's README should contain all relevant information on the case; for example:
    + From which paper or thesis stems this case?
    + which software packages does it couple? 
    + What does it simulate?
    + Which other dependencies are there? E.g., specific ParaView version required to visualize the ouput or a Python version to plot the results.
    + ...
- `dependencies.json`:
  * This file is parsed by the top-level CMake execution to automatically fetch all dependencies that have to be built to run the considered case.
  * It specifies (1.) which repositories and should be automatically fetched when running the example and (2.) their exact state, specified via a commit hash or TAG.
  * For each repo, a name, an url and a commit have to be provided.
  * See `cases/hello_world/dependencies.json` for an example.
  * Note that you should only add those dependencies here that we want to build ourselves, such as, e.g., t8code or MESSy; other dependencies on some pre-installed libraries should be handled by `prepare_on_teamserver.sh` and documented in the `README.md`.
  * The fetched repositories can be found in a subfolder `libs` within your case directory; more precisely, fetching a repository `$SOME_REPO` will create the subfolders:
    + `$SOME_REPO-src`: The repo's clone.
    + `$SOME_REPO-build`: An empty folder for building the repo.
    + `$SOME_REPO-subbuild`: An empty folder for sub-builds.
- `download_files.json` (optional):
  * This optional file allows you to specify individual files that should be downloaded after the dependencies have been installed.
  * Each file entry requires a `url` (the URL to download from) and a `filename` (the name to save the file as).
  * Optionally, you can specify a `target_path` to control where the file is saved (defaults to the case directory).
  * Files are downloaded using CMake's `file(DOWNLOAD)` command, which supports HTTP, HTTPS, and FTP URLs.
  * Example:
    ```json
    {
      "files": [
        {
          "url": "https://example.com/data/mesh.vtu",
          "filename": "input_mesh.vtu",
          "target_path": "data"
        },
        {
          "url": "https://example.com/config/params.yaml",
          "filename": "parameters.yaml"
        }
      ]
    }
    ```
  * The files will be downloaded after the dependencies have been fetched and installed.
- `prepare_on_teamserver.sh`:
  * This script is executed before starting the actual building and running of the case.
  * Since we rely on the AMR Teamserver as reference hardware, this script does everything Teamserver-specific required to run the case; in particular, this means loading the correct modules.
  * Encapsulating the hardware-specific steps in this script makes it simpler to run the case on another system.
  * Typically, this script should at least contain a `module purge` and loading some t8code module.
- `run.sh`:
  * This is the main workflow script of the case considered.
  * It is automatically called from CMake after fetching the dependencies and preparing the Teamserver.
  * The run script is supposed to run all steps required to reproduce the case results in one go.
  * A typical structure could be:
    + configure using cmake
    + build with make or ninja
    + run the simulation
    + do some post-processing.
  * However, we intentionally do not prescribe a fixed corset but instead provide the freedom to deviate from this standard outline.
- `clean.sh`:
  * It is recommended, though not strictly required, to add this shell script to remove all build artifacts to reset the case folder content.
