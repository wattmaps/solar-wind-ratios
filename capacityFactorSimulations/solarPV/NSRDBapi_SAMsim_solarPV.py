# -*- coding: utf-8 -*-
"""
Created on Sun Jan 31 10:29:30 2021
updated: 2/16/2022
updated: 4/21/2022

@author: Grace Wu
"""

import pandas as pd
import numpy as np
import sys, os
import site
import math
#from apscheduler.schedulers.blocking import BlockingScheduler
#import sched
import time
from datetime import datetime
#from PySSC import PySSC
import SAMassumptions_singleAxisTracking_PVwatts
### import SAMassumptions_fixedTilt_v1
# Use site.addsitedir() to set the path to the SAM SDK API.
thisDir = os.path.dirname(__file__)
print('Working directory:    ', thisDir)
site.addsitedir(thisDir)

''' ============================
-1. Choose whether to save the NSRDB weather file to local drive
============================ ''' 
save = "yes"

''' ============================
0. Select PV technology to simulate and column name prefix
============================ ''' 

## choose the technology
tech = "tracking_PVwatts" ## tracking or fixed_PVwatts or tracking_PVwatts

### techAssumptions_dict = {"tracking_PVwatts" : SAMassumptions_singleAxisTracking_PVwatts.singleAxisTracking,
                        ### "fixed_PVwatts" : SAMassumptions_fixedTilt_v1.fixedTilt}

techAssumptions_dict = {"tracking_PVwatts" : SAMassumptions_singleAxisTracking_PVwatts.singleAxisTracking}

colNamePrefix = "CF_" + tech + "_" # 'CF_fixed_' ## or 'CF_singleAxis_' 'CF_singleAxis_noTilt_'

''' ============================
1. Select range of FIDs to run
============================ '''
#// don't need to keep this 
## Choose FID range; about 5000 requests per day
FID_start = 79960
FID_end = FID_start + 5000 ## 83964
  
''' ============================
2. set NSRDB API request inputs
============================ ''' 

## ==============  SET USER INPUTS ================
# Choose solar radiation YEAR
year = '2010'

# Declare all variables as strings. Spaces must be replaced with '+', i.e., change 'John Smith' to 'John+Smith'.
# Your full name, use '+' instead of spaces.
your_name = 'Grace+Wu'

# Your reason for using the NSRDB.
reason_for_use = 'solar+resource+assessment'

# Your affiliation
#your_affiliation = 

# Your email address
#your_email = '

# You must request an NSRDB api key 
#api_key = 

# Please join mailing list so we can keep you up-to-date on new developments.
mailing_list = 'true'

## ============== DO NOT CHANGE ANYTHING BELOW THIS =============
# Set the attributes to extract (e.g., dhi, ghi, etc.), separated by commas.
attributes = 'ghi,dhi,dni,wind_speed,air_temperature,solar_zenith_angle'

# Set leap year to true or false. True will return leap day data if present, false will not. # 2004, 2008, 2012, 2016, 2020, 2024, 2028, 2032
leap_year = 'false' ## NOTE: DO NOT SET THIS TO TRUE. THERE IS A GLITCH. just don't include leap day data even in leap years.

# Set time interval in minutes, i.e., '30' is half hour intervals. Valid intervals are 30 & 60.
interval = '30'

# Specify Coordinated Universal Time (UTC), 'true' will use UTC, 'false' will use the local time zone of the data.
# NOTE: In order to use the NSRDB data in SAM, you must specify UTC as 'false'. SAM requires the data to be in the
# local time zone.
utc = 'false'

''' ============================
3. read csv of lat-longs as pd df
============================ '''

## CHANGE THIS IF YOUR LAT/LONG FILE IS SAVED TO A DIFFERENT LOCATION OR HAS A DIFFERENT FILENAME
loc_filename = 'inputs_outputs/XYCapacity_Factors_FixedTracking_PV_SAM_US'

## change this to the output csv file if you want to append to previous run's results.
df_loc = pd.read_csv(loc_filename + "_SAMsim.csv")

## Add column for output CFs if it's not there
if colNamePrefix + year not in df_loc.columns:
    print("adding new column for CF: " + colNamePrefix + year)
    df_loc[colNamePrefix + year] = np.nan

''' ============================
4. function that runs a single simulation given an FID
============================ '''

def runSimulation(FID):

    ## ONLY RUN IF there is NO CF value for this FID:
    if math.isnan(df_loc.loc[df_loc['FID'] == FID][colNamePrefix + year].iloc[0]):
        
        print("FID: ", FID)
                
        lat = df_loc.loc[df_loc['FID'] == FID, "Lat"].iloc[0]
        lon = df_loc.loc[df_loc['FID'] == FID, "Long"].iloc[0]
        
        '''
        4a.  Request Data From NSRDB using Python API
        The following section shows how to download NSRDB data for a specified year and location.
        
        Declare input variables for api request:¶
        '''
        
        if 0 <= FID < 20000:
            FIDrange = "00_20"
        if 20000 <= FID < 40000:
            FIDrange = "20_40"
        if 40000 <= FID < 60000:
            FIDrange = "40_60"
        if 60000 <= FID < 80000:
            FIDrange = "60_80"
        if 80000 <= FID < 100000:
            FIDrange = "80_100"
        
        ## NSRDB weather csv filename on local drive
        NSRDB_wf_folder = "inputs_outputs/NSRDB_timeSeries_" + year + "_" + FIDrange
        NSRDB_wf = NSRDB_wf_folder  + "/solar_" + year + "_" + str(FID) + ".csv"
        
        ## If there is no csv saved for this FID, then get it using the API
        if not(os.path.exists(NSRDB_wf)):
            
            ## Create directory/folder if it doesn't exist
            if not os.path.exists(NSRDB_wf_folder):
                # Create a new directory because it does not exist
                os.makedirs(NSRDB_wf_folder)
                print("Creating new folder " + NSRDB_wf_folder)
        
            # Declare url string
            url = 'https://developer.nrel.gov/api/solar/nsrdb_psm3_download.csv?wkt=POINT({lon}%20{lat})&names={year}&leap_day={leap}&interval={interval}&utc={utc}&full_name={name}&email={email}&affiliation={affiliation}&mailing_list={mailing_list}&reason={reason}&api_key={api}&attributes={attr}'.format(year=year, lat=lat, lon=lon, leap=leap_year, interval=interval, utc=utc, name=your_name, email=your_email, mailing_list=mailing_list, affiliation=your_affiliation, reason=reason_for_use, api=api_key, attr=attributes)
            
            # Return just the first 2 lines to get metadata:
            #info = pd.read_csv(url, nrows=1)
            # See metadata for specified properties, e.g., timezone and elevation
            #timezone, elevation = info['Local Time Zone'], info['Elevation']
            
            # View metadata
            #info 
              
            # Return all but first 2 lines of csv to get data:
            df = pd.read_csv(url, low_memory=False)#, skiprows=2)
            ## save csv to local drive
            if save == "yes":
                df.to_csv(NSRDB_wf)    
        
        
        ## Otherwise, read the weather file from csv stored in local drive
        else:
            #print("Reading weather file from saved csv")
            df = pd.read_csv(NSRDB_wf, low_memory=False)
        
        
        timezone, elevation = float(df.loc[0,'Local Time Zone']), float(df.loc[0,'Elevation'])
        
        ## drop the metadata rows
        df.drop(0, inplace = True)
        
        ## make the first row the header
        new_header = df.iloc[0] #grab the first row for the header
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
        #print(capacity_factor)
        ## add CF to the df
        df_loc.loc[df_loc['FID'] == FID, colNamePrefix + year] = capacity_factor
        

        

''' ============================
5. function that runs simulation given a list of FIDs 
    -  if there is an error, saves run to csv then pauses before trying again
    -  if it completes without an error, saves the runs to csv
============================ '''


def runSimulationLoop(FID_list):
    i = 0
    for FID in FID_list:
        while True:
            try: 
                i = i + 1
                #print(i)
                runSimulation(FID)
                if i == 300:
                    df_loc.to_csv(loc_filename + "_SAMsim.csv", index=False)
                    print("Saved to file")
                    i = 0
            except Exception as exc:
                print(exc)
                ## save CSV to file
                df_loc.to_csv(loc_filename + "_SAMsim.csv", index=False)
                ## PAUSE
                time.sleep(5)
                continue
            break
             
    ## save CSV to file
    df_loc.to_csv(loc_filename + "_SAMsim.csv", index=False)
 

''' ============================
6. Run functions
============================ '''

FID_list_in = list(range(FID_start,FID_end,1))
runSimulationLoop(FID_list_in)  

'''
## Schedule runs every hour
    ## https://pymotw.com/2/sched/
scheduler = sched.scheduler(time.time, time.sleep)
for i in range(2, 16,1):
    dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    print("date and time =", dt_string)
    print("batch", i, "scheduled time:", i, "hour")
    print(range(999*i,999*(i+1),1))
    FID_list_in = list(range(999*i,999*(i+1),1))
    scheduler.enter(3600 * i, 1, runSimulationLoop, (FID_list_in,))

scheduler.run()
'''