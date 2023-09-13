# Data consolidation pipeline for multisensor group studies

This repository contains a set of scripts to accomplish the following tasks:
* Detect when SD cards and SD card readers are connected to the machine
* Isolate the project-specific files for organization
* Use file metadata to organize into directory tree structure

In the video domain:
* Find the relevant video files (avoiding .LRV and .TH files)
* Concatenate the appropriate files
* Run video alignment using the audio outputs associated with the video files

In the audio domain:
* Get the appropriate files

# TO-DO's
* Change naming conventions of concatenated videos to include full experimental info (do this for all saved files)
* Add a function to check if the SD card is mounted
* Fashion a means of determining which camera is in which position (e.g., front, back, left, right)

