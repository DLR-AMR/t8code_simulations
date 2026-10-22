# Case README: Hello World File Download

## Case description

This simple example case demonstrates the file download feature.
It downloads a simple '.txt' file from the t8data repository and prints its contents.
This example has no other dependencies and does not run any code.

Should your use cases require any additional files, you can specify them
in a `download_files.json` file. See the [project README](../../README.md) for more details.


## Workflow

The `run.sh` script executes the following main steps:
* Print the file contents of 't8data_helloworld.txt' after it was downloaded by CMake.

## Dependencies

### Fetched repositories

None

### Teamsverver modules

None

### Other dependencies

* File Download from [t8data](https://github.com/dlr-amr/t8data)

## Contact person:

johannes.holke@dlr.de