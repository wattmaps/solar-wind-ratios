"""
@author: https://github.com/wattmaps
""" 

### -----------------------
# Loading packages & defaults
### -----------------------
import pandas as pd
import os
import time as time

current_dir = os.getcwd()
#current_dir should be your local path to the solar-wind-ratios folder
print(current_dir)

### -----------------------
# Reading in the yearly data & setting folder path
### -----------------------
# Load data from all years
# to get a file per PID for the solar data change the file paths below to 'data/SAM/SAM_solar_2012.csv', 'data/SAM/SAM_solar_2013.csv', 'data/SAM/SAM_solar_2014.csv',
df_cf_2012 = pd.read_csv(os.path.join(current_dir, 'data/SAM/SAM_wind_2012.csv'))
df_cf_2013 = pd.read_csv(os.path.join(current_dir, 'data/SAM/SAM_wind_2013.csv'))
df_cf_2014 = pd.read_csv(os.path.join(current_dir, 'data/SAM/SAM_wind_2014.csv'))

# Define the folder where the output files will be saved
# for solar define the folder to the 'data/solarCapacityFactorFilePerPID' file path
folder = os.path.join(current_dir, 'data/windCapacityFactorFilePerPID')

### -----------------------
# Reshaping the data & reading it as a csv for each PID
### -----------------------

# initializing the counter variable
counter = 0

# Loop through each row of the dataframe and extract data for that location
for i in range(df_cf_2012.shape[0]):
    location_data_2012 = df_cf_2012.iloc[i, 5:].values.tolist()
    location_data_2013 = df_cf_2013.iloc[i, 5:].values.tolist()
    location_data_2014 = df_cf_2014.iloc[i, 5:].values.tolist()  # add this line
    location_name = df_cf_2012.iloc[i, 0]
    
    # Create a new dataframe containing the hourly energy data for both years
    location_df_2012 = pd.DataFrame({'energy_generation': location_data_2012})
    location_df_2013 = pd.DataFrame({'energy_generation': location_data_2013})
    location_df_2014 = pd.DataFrame({'energy_generation': location_data_2014})  # add this line

    # adding a new column with the hour and year index
    location_df_2012['hour'] = range(1, 8761)
    location_df_2013['hour'] = range(8761, 17521)
    location_df_2014['hour'] = range(17521, 26281)  # add this line

    # Concatenate the dataframes and sort by hour
    location_df = pd.concat([location_df_2012, location_df_2013, location_df_2014]).sort_values('hour')  # update this line

    # Save the new dataframe as a CSV file with the location name as the file name
    location_df.to_csv(f'{folder}/capacity_factor_PID{location_name}.csv', index = False)
    
    counter += 1
    # increment the counter and print an update statement every 200 files saved
    if counter % 200 == 0:
        print(f"Saved files for the PID {counter}.")


