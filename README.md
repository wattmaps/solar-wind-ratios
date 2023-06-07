# solar-wind-ratios
This repository contains Python and R scripts for the iterative acquisition of hourly meteorological data and modeled energy generation for each resource at each existing wind project within the contiguous U.S. This repository also contains scripts to build and solve a nonlinear optimization model to find the optimal amount of solar PV that maximizes annual profit. 

The repository is structured so that each phase is housed in a separate folder:
- dataCleaningProcessing
- capacityFactorSimulations
- optimizationModel

This repository also includes a structure diagram, `solar_wind_ratios_repo_diagram.pdf`. This diagram includes the structure of how data objects were stored locally for reproducibility and ease of use. 

### dataCleaningProcessing
This folder houses the `converting_wind_data_to_PIDs.Rmd` that walks users through obtaining point coordinates for existing wind projects. These point coordinates are used in the next step to obtain meteorological data and simulated energy production for wind and solar PV at existing wind project.

### capacityFactorSimulations
This folder houses the code required to pull hourly meteorological data through NREL NSRDB API and WIND Toolkit API and obtain simulated hourly capacity factors through NREL System Adivsor Model via the pySCC API over the period of interest at each existing wind project.
- `solarPV`: This folder contains the script and assumptoions used to pull meteorological data and run SAM for solar PV. 
- `wind`: This folder contains the script and assumptions used to pull meteorological data and run SAM for wind. 

### optimizationModel
This folder contains code used to format the output from the capacityFactorSimulations scripts for the nonlinear optimization model and the script used to build and solve the model. 
