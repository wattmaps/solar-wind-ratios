# loading packages
import requests
import pandas as pd
import time
from io import StringIO 
from dotenv import load_dotenv
import site
import numpy as np
import sys, os
import math
import time
from datetime import datetime
import time


current_dir = os.getcwd()
#current_dir should be your local path to the solar-wind-ratios folder
print(current_dir)

# defining a working directory
thisDir = os.path.join(current_dir, 'capacityFactorSimulations/solarPV')
print('Working directory:  ', thisDir)
site.addsitedir(thisDir)

import SAMassumptions_singleAxisTracking_PVwatts_hourly
''' ============================
-1. Choose whether to save the NSRDB weather file to local drive
============================ ''' 
save = "yes"


''' ============================
0. Select PV technology to simulate and column name prefix
============================ ''' 

tech = "tracking_PVwatts" 

techAssumptions_dict = {"tracking_PVwatts" : SAMassumptions_singleAxisTracking_PVwatts_hourly.singleAxisTracking}

colNamePrefix = "CF_status"

''' ============================
1. Select range of PIDs to run
============================ '''

PID_start = 1
PID_end = PID_start + 1335

''' ============================
2. set NSRDB API request inputs
============================ ''' 

## ==============  SET USER INPUTS ================
# Choose solar radiation YEAR
year = '2014'

# Declare all variables as strings. Spaces must be replaced with '+', i.e., change 'John Smith' to 'John+Smith'.
# Your full name, use '+' instead of spaces.
your_name = 'Alessandra+Vidal'

# Your reason for using the NSRDB.
reason_for_use = 'colocation+assessment'

# Your affiliation
your_affiliation = 'UCSB'

# Your email address
your_email = 'avidalmeza@bren.ucsb.edu'

# You must request an NSRDB api key 
# store your API key in a .env file located inside the capacityFactorSimulations folder
dotenv_path = os.path.join(os.path.dirname(thisDir), ".env") 
load_dotenv(dotenv_path)
COLLEEN_API = os.getenv('nrel_colleen2')
ALESSANDRA_API = os.getenv('nrel_alessandra')
MICHELLE_API = os.getenv('nrel_michelle')
api_key = ALESSANDRA_API

# Please join mailing list so we can keep you up-to-date on new developments.
mailing_list = 'true'

## ============== DO NOT CHANGE ANYTHING BELOW THIS =============
# Set the attributes to extract (e.g., dhi, ghi, etc.), separated by commas.
attributes = 'ghi,dhi,dni,wind_speed,air_temperature,solar_zenith_angle'

# Set leap year to true or false. True will return leap day data if present, false will not. # 2004, 2008, 2012, 2016, 2020, 2024, 2028, 2032
leap_year = 'false' ## NOTE: DO NOT SET THIS TO TRUE. THERE IS A GLITCH. just don't include leap day data even in leap years.

# Set time interval in minutes, i.e., '30' is half hour intervals. Valid intervals are 30 & 60.
interval = '60'

# Specify Coordinated Universal Time (UTC), 'true' will use UTC, 'false' will use the local time zone of the data.
# NOTE: In order to use the NSRDB data in SAM, you must specify UTC as 'false'. SAM requires the data to be in the
# local time zone.
utc = 'false'

''' ============================
3. read csv of lat-longs as pd df
============================ '''

## CHANGE THIS IF YOUR LAT/LONG FILE IS SAVED TO A DIFFERENT LOCATION OR HAS A DIFFERENT FILENAME # (CHANGED FOR DIFFERENT PIDs)
loc_filename = os.path.join(current_dir, 'data/us_PID_cords.csv')

df_loc = pd.read_csv(loc_filename, engine = 'python')

## Add columns for output CFs if it's not there
if colNamePrefix not in df_loc.columns:
    print("adding new columns for status and hourly capacity factor")
    df_loc[colNamePrefix] = np.nan
    print("adding new columns for hourly capacity factors")
    new_cols = [f'cf_hour_{i}' for i in range(8760)]
    df_loc = df_loc.reindex(columns = df_loc.columns.tolist() + new_cols)
    
# create a file path to where you want to save the simulation output for a given year
output_filename = current_dir + "/data/SAM/SAM_solar_" + year + ".csv"

''' ============================
4. function that runs a single simulation given an PID
============================ '''

def runSimulation(PID):
    ## define df_loc as a global value so you can reassign it in the function
    #global df_loc
    ## ONLY RUN IF there is NO status value for this PID:
    if math.isnan(df_loc.loc[df_loc['PID'] == PID]['cf_hour_0'].iloc[0]):
        
        print("PID: ", PID)
                
        lat = df_loc.loc[df_loc['PID'] == PID, "lat"].iloc[0]
        lon = df_loc.loc[df_loc['PID'] == PID, "lon"].iloc[0]
        p_cap = df_loc.loc[df_loc['PID'] == PID, "p_cap"].iloc[0]

        '''
        4a.  Request Data From NSRDB using Python API
        The following section shows how to download NSRDB data for a specified year and location.
        '''
        ## NSRDB weather csv filename on local drive
        NSRDB_wf_folder = current_dir + "/data/NSRDB/solarTimeSeries" + year
        NSRDB_wf = NSRDB_wf_folder  + "/solar_" + year + "_" + str(PID) + ".csv"
        
        ## If there is no csv saved for this PID, then get it using the API
        if not(os.path.exists(NSRDB_wf)):
            
            ## Create directory/folder if it doesn't exist
            if not os.path.exists(NSRDB_wf_folder):
                # Create a new directory because it does not exist
                 os.makedirs(NSRDB_wf_folder)
                 print("Creating new folder " + NSRDB_wf_folder)

            # Declare url string and store as csv
            url = 'https://developer.nrel.gov/api/solar/nsrdb_psm3_download.csv?wkt=POINT({lon}%20{lat})&names={year}&leap_day={leap}&interval={interval}&utc={utc}&full_name={name}&email={email}&affiliation={affiliation}&mailing_list={mailing_list}&reason={reason}&api_key={api}&attributes={attr}'.format(year=year, lat=lat, lon=lon, leap=leap_year, interval=interval, utc=utc, name=your_name, email=your_email, mailing_list=mailing_list, affiliation=your_affiliation, reason=reason_for_use, api=api_key, attr=attributes)

            df = pd.read_csv(url, engine = 'python')

            ## save csv to local drive
            if save == "yes":
                df.to_csv(NSRDB_wf)    
        ## Otherwise, read the weather file from csv stored in local drive
        else:
            print("Reading weather file from saved csv")
            df = pd.read_csv(NSRDB_wf, engine = 'python')
    
        timezone, elevation = float(df.loc[0,'Local Time Zone']), float(df.loc[0,'Elevation'])

        ## drop the metadata rows
        df.drop(0, inplace = True)

        ## make the first row the header
        new_header = df.loc[1] #grab the first row for the header
        df_data = df[1:] #take the data less the header row
        df_data.columns = new_header #set the header row as the df header

        ## convert all string/objects to numbers
        df_data = df_data.apply(pd.to_numeric) 
    
        if leap_year == "false":
            minInYear = 525600 # fewer min in a non-leap year
        else:
            minInYear = 527040 ## more minutes in a leap year

        # Set the time index in the pandas dataframe:
        df_data = df_data.set_index(pd.date_range('1/1/{yr}'.format(yr=year), freq=interval+'Min', periods=minInYear/int(interval)))

        ''' 
        4b. Call SAM Simulation function from module 
        '''

        simulationFunct = techAssumptions_dict[tech]
        capacity_factor = simulationFunct(homePath = thisDir,
                                          lat_in = lat,
                                          lon_in = lon,
                                          timezone_in = timezone,
                                          elevation_in = elevation,
                                          df_data_in = df_data)

        # filter for PID in df_loc dataframe and select the columns from cf_hour_0 till the end
        selected_PID_row = df_loc.loc[df_loc['PID']== PID, 'cf_hour_0':]
        # reshape the capacity_factor series so that instead of 8760 rows and 1 column it has 8760 columns and 1 row
        capacity_factor_reshape = np.transpose(capacity_factor)
        # updates all the rows and columns in selected_PID_row dataframe with capacity_factor_reshape
        # selected_PID_row has the same dimensions as capacity_factor_reshape after taking the transpose
        selected_PID_row[:] = capacity_factor_reshape
        # update the original df_loc dataframe with values for the hourly capacity factor
        df_loc.loc[df_loc['PID'] == PID, 'cf_hour_0':] = selected_PID_row
        # add an indicator in the colNamePrefix column in df_loc to show that it has been run
        df_loc.loc[df_loc['PID'] == PID, colNamePrefix] = 1

''' ============================
5. function that runs simulation given a list of PIDs 
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