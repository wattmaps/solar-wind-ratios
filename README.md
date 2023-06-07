# solar-wind-ratios

This repository contains R Markdown and Python scripts for the iterative acquisition of hourly meteorological data and modeled energy generation for each technology at each existing wind project within the contiguous U.S. Additionally, it contains scripts to run a nonlinear optimization to find the amount of solar PV at existing wind projects that maximizes profit. The repository is structured so that each phase of the analysis is housed in a separate folder. 

## dataCleaningProcessing
This folder houses the converting_wind_data_to_PIDs.Rmd that walks users through obtaining point coordinates for existing wind projects. These point coordinates are used in the next step to obtain meteorological data and simulated energy production for wind and solar PV at existing wind project.

## capacityFactorSimulations
This folder houses the code required to pull hourly meteorological data through NREL's NSRDB API and Windtoolkit API and obtain simulated hourly capacity factors through NREL's System Adivsor Model (SAM) via the pySCC API over 3 years for each wind project.

### solarPV
This folder contains the script and assumptoions used to pull meteorological data and run SAM for solar PV. 

### wind
This folder contains the script and assumptions used to pull meteorological data and run SAM for wind. 

## optimizationModel
This folder contains code used to format the output from the capacityFactorSimulations scripts for the optimization model and the script used to run the optimization. 

# Repo Structure Diagram
Please reference the solar_wind_ratios_repo_diagram.pdf in this repository for a full diagram of the files and folders. It also includes the structure of how data was stored locally for reproducibility and ease of use. 
