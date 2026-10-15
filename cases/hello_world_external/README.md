# Case README: Hello World External

## Case description

This simple example case covers a hello-world program, compiled as a separate project that links against t8code. It is supposed to demonstrate the usage of this repository and mimic the basic steps required to include an external executable.

## Workflow

The `run.sh` script executes the following main steps:
* Configure, build, and install t8code.
* Configure and compile the hello-world project.
* Run the resulting executable, piping its output to a log file.
* Do some pseudo-post-processing, that is, printing the log file to screen.

## Dependencies

### Fetched repositories

* `t8code` from `https://github.com/DLR-AMR/t8code`.

### Teamsverver modules

`t8code/t8code-development-gcc13-mpich`

### Other dependencies

* MPI version 3.0 or higher
* C++ compiler supporting C++20
* ...

## Contact person:

thomas.spenke@dlr.de