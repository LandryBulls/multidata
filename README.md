# Data consolidation pipeline for multisensor group studies

This repository contains a set of scripts to accomplish the following tasks:
* Detect when SD cards and SD card readers are connected to the machine
* Add multiple checkpoints and logging of data dates, experiment numbers, etc
* Isolate the project-specific files for organization
* Use file metadata to organize into directory tree structure
* Concatenate the appropriate video files
* Run video alignment using the audio outputs associated with the video files
* Pull survey data from Qualtrics and add to the folder

# TO-DO's
* Add equirectangular conversion code and run integrated test 
* Add PyQT interface and more descriptive feedback signals (I e. what stage the script is in)
* Change naming conventions of concatenated videos to include full experimental info (do this for all saved files)
* Fashion a means of determining which camera is in which position (e.g., front, back, left, right)
* Add Qualtrics survey data pull code 

