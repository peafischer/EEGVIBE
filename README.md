# Introduction

This repository contains a workflow for running closed-loop EEG experiments with some stimulation fed back to the participant. The stimulation feedback is triggered on a target phase of a target frequency of the EEG signal. 

In order to minimise computation delays, the workflow is split into components that are ran concurrently or in parallel (using `threading.Thread` or `multiprocessing.Process` respectively). The components implemented until now are reading (`read.py`), writing (`write.py`), analysing EEG & stimulation (`analysis.py`) and plotting (`plot.py`).

The workflow is then organised as : reading `->` analysis `->` plotting **AND** reading `->` writing .

Each component communicates with the components that it connects to or is connected to using [`ZMQ`](https://pyzmq.readthedocs.io/en/latest/index.html), a message-passing protocol. This choice was inspired by [Autopilot](https://auto-pi-lot.com/), an open-source package for running distributed behavioral experiments on Raspberry Pis. For a great introduction into `ZMQ` in Python for scientists, check out this tutorial: [Part 1](https://www.pythonforthelab.com/blog/using-pyzmq-for-inter-process-communication-part-1/) and [Part 2](https://www.pythonforthelab.com/blog/using-pyzmq-for-inter-process-communication-part-2/).

# Installation

This repository is not a registered Python package (yet). In order to use it, one would need to clone the repository and then use their favorite environment manager (e.g. `conda`, `venv` or `virtualenv`). Use the `requirements.txt` on a new environment to install most of dependencies of `EEGVIBE`. The commands to create a new environment and install dependencies from `requirements.txt` depend on the environment manager used, but they are all relatevely easy to find online.

`EEGVIBE` is not yet a registered package as it depends on `eego_sdk` for reading in EEG signals from an amplifier. The `eego_sdk` package is a Python wrapper on a C++ library that needs to be built (using CMake) and linked to the current project or simply added to `PYTHONPATH` so Python knows what to do at `import eego_sdk`. Check the [wrapper repository](https://gitlab.com/smeeze/eego-sdk-pybind11) for instructions or contact Dr Petra Fischer for more details.

# Workflow components

## Reading

Includes functions for reading data from an EEG amplifier (`read_from_stream`) or from an `.HDF5` or `.csv.` file containing stored data from a previous recording sesion (`read_from_file`). The latter option is useful when developing new components and debugging them and/or being away from the lab where the EEG amplifier is.

## Analysis

This component includes two modes: 
- running the feedback loop, that is tracking the phase of the target frequency from one EEG signal channel and triggering stimulations when the target phase is reached.

- replaying a stimulation schedule. This is an open-loop mode, where there are no frequency & phase targets on the EEG signal. All stimulation from a previous experiment are replayed at exactly the same timepoints as they were originally triggered, relative to the beginning of the experiment.

## Plotting

Includes a function (`plot_stream`) that creates a `Qt` plotting widget and updates it online as new EEG samples are read. The channel that is tracked (see [Analysis section](#analysis)) is plotted by default, and more channels (e.g. EMG data channels) can be added to the same axes. A vertical offset is introduces to better distinguish between signals.

## Writing

Component for storing data into files. By default the `HDF5` format is used and data is stored in chunks, to make writing more efficient. Using `HDF5` over other formats like `csv` also makes reading data much faster, either when used to `read_from_file` or for offline analysis after the recording session.

# Using EEGVIBE

There are two ways of using `EEGVIBE`. The more user-friendly and less flexible way is to use the functions in `eegvibe/run.py`. These are wrappers around a closed-loop recording workflow (`run_tracking`) and a replay workflow (`run_replay`). They come with docstrings that explain all of their arguments. 

Alternatively, one can adapt these `run_` functions to their own workflow, e.g. by using different EEG filters, different phase tracking algorithms or different plots. This is a more modular approach, where one can pick and choose which components to use and which to change/extend to come up with their own workflow like the ones in `eegvibe/run.py`.
