
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


start_time = time.time()
# defining a working directory
thisDir = os.path.dirname(r"C:\Code\sam-generation\wind\data")
print('Working directory:    ', thisDir)
site.addsitedir(thisDir)

import SAMassumptions_hourly_wind_wf_9

# saving the windtoolkit data folder w/out the year
wtk_folder_path = r'C:\Code\sam-generation\wind\data\timeSeries_'

''' ============================
Reading in the SAM Assumptions
============================ '''

# saving assmptions as a techAssumptions dictionary
techAssumptions_dict = {"onshore_wind" : SAMassumptions_hourly_wind_wf_9.onshoreWind}
tech = "onshore_wind"
colNamePrefix = "CF_status" 

''' ============================
Loading API Keys from Environment File
============================ '''

### Retrieving the dot env path
dotenv_path = os.path.join(os.path.dirname(thisDir), ".env")

### Reading data from .env file
load_dotenv(dotenv_path) # reading in the environment variables inside .env

### Storing URL variables for each user
# loading the api key from the environment file for each users
COLLEEN_API = os.getenv('nrel_colleen3')
ALESSANDRA_API = os.getenv('nrel_alessandra3')
MICHELLE_API = os.getenv('nrel_michelle')
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
year = 2012

#specifying the windtoolkitfolder for the year provided
wtk_folder = str(wtk_folder_path) + str(year)

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
loc_filename = r"C:\Code\sam-generation\wind\data\wind_capacity_factor_2012_missing_dat_run_04.23.csv"
df_loc = pd.read_csv(loc_filename)
df_url = df_loc

## Add columns for output CFs if it's not there
if colNamePrefix not in df_loc.columns:
    print("adding new columns for status and hourly capacity factor")
    df_loc[colNamePrefix] = np.nan
    print("adding new columns for hourly capacity factors")
    new_cols = [f'cf_hour_{i}' for i in range(8760)]
    df_loc = df_loc.reindex(columns = df_loc.columns.tolist() + new_cols)


# saving the windtoolkit data folder w/out the year
# DELETE wtk_folder_path = r'C:\Code\sam-generation\wind\data\timeSeries_'

''' ============================
LOOP 1: Creating unique URLs with WIND Toolkit API request inputs
============================ ''' 

df_url['url'] = ''  # create an empty column for the URLs
for index, row in df_url.iterrows():
    # extract FID, latitude, and longitude from the row
    fid = row['FID']
    lat = row['lat']
    lon = row['lon']
    
    # create a unique URL for this FID
    
    # colleen
    url = f"https://developer.nrel.gov/api/wind-toolkit/v2/wind/wtk-srw-download?api_key={cm_key}&lat={lat}&lon={lon}&year={year}&email={cm_email}"
    #url = f"https://developer.nrel.gov/api/wind-toolkit/v2/wind/wtk-srw-download?api_key={cm_key2}&lat={lat}&lon={lon}&year={year}&email={cm_email2}"
    #url = f"https://developer.nrel.gov/api/wind-toolkit/v2/wind/wtk-srw-download?api_key={cm_key3}&lat={lat}&lon={lon}&year={year}&email={cm_email3}"
    
    # ale
    # url = f"https://developer.nrel.gov/api/wind-toolkit/v2/wind/wtk-srw-download?api_key={avm_key}&lat={lat}&lon={lon}&year={year}&email={avm_email}"
    
    # michelle
    #url = f"https://developer.nrel.gov/api/wind-toolkit/v2/wind/wtk-srw-download?api_key={ml_key}&lat={lat}&lon={lon}&year={year}&email={ml_email}"

    # add the URL to the df_loc dataframe
    df_url.loc[index, 'url'] = url


df_url # renaming location dataframe to url dataframe
url = df_url.loc[1, 'url'] # check the url

''' ============================
LOOP 2: Run through each url to pull meterological data and SAM simulation
============================ '''

for index, row in df_url.iterrows():
    
    # extract the FID and the url from the row
    FID = row['FID']
    url = row['url']
    lat = row['lat']
    lon = row['lon']

    # calling the WIND toolkit API for a url 
    response = requests.get(url)

    df_data_in = "\wind_" + str(year) + "_" + str(FID) + ".srw"
    wind_wf = str(wtk_folder) + df_data_in


    # saving the WIND toolkit data as an srw file
    if response.status_code == 200:
        
         with open(wind_wf, "w") as f:
             f.write(response.text)
         wind_wf_byte = wind_wf.encode()
         simulationFunct = techAssumptions_dict[tech]
         capacity_factor = simulationFunct(homePath = thisDir,
                                                lat_in = lat,
                                                lon_in = lon,
                                                data_in = wind_wf_byte)
         print(capacity_factor)
         # filter for FID in df_loc datagrame and select the columns from cf_hour_0 till the end
         selected_FID_row = df_loc.loc[df_loc['FID'] == FID, 'cf_hour_0':]
         #reshape the capcity_factor series that instead of 8760 rosw and 1 column it has 8760 columns and 1 row
         capacity_factor_reshape = np.transpose(capacity_factor)
         # updates all the rows and columns in selected_FID_row dataframe with capcity factor reshaped data
         # selected_FID_row has the same dimensions as capacity_factor_reshaped after taking the transpose
         selected_FID_row[:] = capacity_factor_reshape
         # update the original df_loc dataframe with values for the hourly capacity factor
         df_loc.loc[df_loc['FID'] == FID, 'cf_hour_0':] = selected_FID_row
         # add an indicator in the colNamePrefix column in df_loc to show that it has been run
         df_loc.loc[df_loc['FID'] == FID, colNamePrefix] = 'done'  
    else:
        df_loc.to_csv(f'C:\Code\sam-generation\wind\data\wind_capacity_factor_missing_dat_4.23run_{year}.csv', index = False)
        print(f"Failed to download data for: {FID} and has an error code of {response.status_code}")

df_loc.to_csv(f'C:\Code\sam-generation\wind\data\wind_capacity_factor_missing_dat_4.23run_{year}.csv', index = False)

end_time = time.time() # End the timer

print("Time taken:", end_time - start_time, "seconds.") # Print the time taken by the script

df_loc
