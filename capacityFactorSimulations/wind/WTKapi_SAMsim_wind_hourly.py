
''' ============================
Importing Packages & Directory
============================ ''' 

# loading libraries, packages & modules
import requests
import pandas as pd
import time
from io import StringIO 
from dotenv import load_dotenv
import site
import numpy as np
import sys, os
import math
#from apscheduler.schedulers.blocking import BlockingScheduler
#import sched
import time
from datetime import datetime
from PySAM.ResourceTools import SRW_to_wind_data
import socket
import time


current_dir = os.getcwd()
#current_dir should be your local path to the solar-wind-ratios folder
print(current_dir)

# defining a working directory
thisDir = os.path.join(current_dir, 'capacityFactorSimulations/wind')
print('Working directory:    ', thisDir)
site.addsitedir(thisDir)

import SAMassumptions_hourly_wind

# saving the windtoolkit data folder w/out the year
# wtk_folder_path = r'C:\Code\sam-generation\wind\data\meteorologicalData_'

''' ============================
Choose whether to save the Wind Toolkit weather file to local drive
============================ ''' 
save = "yes"

''' ============================
Reading in the SAM Assumptions
============================ '''

# saving assmptions as a techAssumptions dictionary
techAssumptions_dict = {"onshore_wind" : SAMassumptions_hourly_wind.onshoreWind}
tech = "onshore_wind"
colNamePrefix = "CF_status" 

''' ============================
1. Select range of PIDs to run
============================ '''

PID_start = 1
PID_end = PID_start + 1335


''' ============================
Loading API Keys from Environment File
============================ '''

### Retrieving the dot env path
# store your API key in a .env file located inside the capacityFactorSimulations folder
dotenv_path = os.path.join(os.path.dirname(thisDir), ".env")

### Reading data from .env file
load_dotenv(dotenv_path) # reading in the environment variables inside .env

### Storing URL variables for each user
# loading the api key from the environment file for each users
COLLEEN_API = os.getenv('nrel_colleen3')
ALESSANDRA_API = os.getenv('nrel_alessandra3')
MICHELLE_API = os.getenv('nrel_michelle3')
COLLEEN2_API = os.getenv('nrel_colleen2')
COLLEEN3_API = os.getenv('nrel_colleen3')

''' ============================
Setting API Inputs to Loop Through
============================ ''' 

## ==============  SET USER INPUTS ================

# storing api parameters for Colleen
cm_key = COLLEEN_API
cm_email = "colleenrmccamy@gmail.com"
cm_key2 = COLLEEN2_API
cm_email2 = "colleenrmccamy@gmail.com"
cm_key3 = COLLEEN3_API
cm_email3 = "colleen.rebecca.mc@gmail.com"

# storing api parameters for Michelle
ml_key = MICHELLE_API
# ml_email = "michellelam@bren.ucsb.edu"
# ml_email = "michellelam777@gmail.com"
ml_email = "michellelam@ucsb.edu"

# storing api parameters for Ale
avm_key = ALESSANDRA_API
avm_email = "avidalmeza@bren.ucsb.edu"

## ==============  SET PARAMETER INPUTS ================



# Specifying year for each API run (year 1 is the year for the first set of URLs)
### CHANGE FOR EACH RUN
year = '2012'

#specifying the windtoolkitfolder for the year provided
# wtk_folder = str(wtk_folder_path) + str(year)

# Specify Coordinated Universal Time (UTC), 'true' will use UTC, 'false' will use the local time zone of the data.
# NOTE: In order to use the NSRDB data in SAM, you must specify UTC as 'false'. SAM requires the data to be in the
# local time zone.
utc = 'false'

## ============== I THINK WE CAN REMOVE FOR WIND =============

# Set leap year to true or false. True will return leap day data if present, false will not. # 2004, 2008, 2012, 2016, 2020, 2024, 2028, 2032
leap_year = 'false' ## NOTE: DO NOT SET THIS TO TRUE. THERE IS A GLITCH. just don't include leap day data even in leap years.

# Specifying wind hub height parameters (static for this API call)
hubheight = 100

# Set time interval in minutes, i.e., '60' is hour intervals.
# interval = '60'

''' ============================
Read csv of candidate project areas lat/longs
============================ ''' 
## NOTE: CHANGE THIS IF YOUR LAT/LONG FILE IS SAVED TO A DIFFERENT LOCATION OR HAS A DIFFERENT FILENAME

# read csv of lat-longs as pd df
loc_filename = os.path.join(current_dir, 'data/us_PID_cords.csv')
df_loc = pd.read_csv(loc_filename)
#df_url = df_loc

## Add columns for output CFs if it's not there
if colNamePrefix not in df_loc.columns:
    print("adding new columns for status and hourly capacity factor")
    df_loc[colNamePrefix] = np.nan
    print("adding new columns for hourly capacity factors")
    new_cols = [f'cf_hour_{i}' for i in range(8760)]
    df_loc = df_loc.reindex(columns = df_loc.columns.tolist() + new_cols)

# create a file path to where you want to save the simulation output for a given year
output_filename = current_dir + "/data/SAM/SAM_wind_" + year + ".csv"

''' ============================
Function that runs a single simulation given an PID
============================ '''

def runSimulation(PID):

    ## ONLY RUN IF there is NO status value for this PID:
    if math.isnan(df_loc.loc[df_loc['PID'] == PID]['cf_hour_0'].iloc[0]):
        
        print("PID: ", PID)
                
        lat = df_loc.loc[df_loc['PID'] == PID, "lat"].iloc[0]
        lon = df_loc.loc[df_loc['PID'] == PID, "lon"].iloc[0]
        #p_cap = df_loc.loc[df_loc['PID'] == PID, "p_cap"].iloc[0]
        #p_cap_kw = p_cap * 1000

        '''
        Request Data From Windtoolkit using Python API
        The following section shows how to download Windtoolkit data for a specified year and location.
        '''
        ## Windtoolkit weather srw filename on local drive
        wtk_wf_folder = current_dir + "/data/Windtoolkit/windTimeSeries" + year
        wtk_wf = wtk_wf_folder  + "/wind_" + year + "_" + str(PID) + ".srw"
        
        ## If there is no csv saved for this PID, then get it using the API
        if not(os.path.exists(wtk_wf)):
            
            ## Create directory/folder if it doesn't exist
            if not os.path.exists(wtk_wf_folder):
                # Create a new directory because it does not exist
                 os.makedirs(wtk_wf_folder)
                 print("Creating new folder " + wtk_wf_folder)

            # Declare url string and store as srw
            url = f"https://developer.nrel.gov/api/wind-toolkit/v2/wind/wtk-srw-download?api_key={cm_key}&lat={lat}&lon={lon}&year={year}&email={cm_email}"
            
            response = requests.get(url)
            
            # saving the WIND toolkit data as an srw file
            if save == "yes":
        
                with open(wtk_wf, "w") as f:
                    f.write(response.text)

            wind_wf_byte = wtk_wf.encode()

        ## Otherwise, read the weather file from srw stored in local drive
        else:
            print("Reading weather file from saved srw")
            wind_wf_byte = wtk_wf.encode()

        ''' 
        Call SAM Simulation function from module 
        '''
        simulationFunct = techAssumptions_dict[tech]
        capacity_factor = simulationFunct(homePath = thisDir,
                                           lat_in = lat,
                                           lon_in = lon,
                                           data_in = wind_wf_byte)
        print(f"Completed {PID}")
        # filter for PID in df_loc dataframe and select the columns from cf_hour_0 till the end
        selected_PID_row = df_loc.loc[df_loc['PID'] == PID, 'cf_hour_0':]
        #reshape the capcity_factor series that instead of 8760 rosw and 1 column it has 8760 columns and 1 row
        capacity_factor_reshape = np.transpose(capacity_factor)
        # updates all the rows and columns in selected_PID_row dataframe with capcity factor reshaped data
        # selected_PID_row has the same dimensions as capacity_factor_reshaped after taking the transpose
        selected_PID_row[:] = capacity_factor_reshape
        # update the original df_loc dataframe with values for the hourly capacity factor
        df_loc.loc[df_loc['PID'] == PID, 'cf_hour_0':] = selected_PID_row
        # add an indicator in the colNamePrefix column in df_loc to show that it has been run
        df_loc.loc[df_loc['PID'] == PID, colNamePrefix] = 1 

''' ============================
Function that runs simulation given a list of PIDs 
    -  if there is an error, saves run to csv then pauses before trying again
    -  if it completes without an error, saves the runs to csv
============================ '''

def runSimulationLoop(PID_list):
    i = 0 
    for PID in PID_list:
        while True:
            try: 
                i = i + 1
                #print(i)
                runSimulation(PID)
                if i == 300:
                    df_loc.to_csv(output_filename, index=False)
                    print("Saved to file")
                    i = 0
            except Exception as exc:
                print(exc)
                ## save CSV to file
                df_loc.to_csv(output_filename, index=False)
                ## PAUSE
                time.sleep(5)
                continue
            break
             
    ## save CSV to file
    df_loc.to_csv(output_filename, index=False)
    
''' ============================
6. Run functions
============================ '''
start_time = time.time()
PID_list_in = list(range(PID_start,PID_end,1))
runSimulationLoop(PID_list_in)  
end_time = time.time()
print("Time taken:", end_time - start_time, "seconds") # Print how long it takes to run the loop 
