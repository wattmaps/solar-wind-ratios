### -----------------------
# Loading packages & defaults
### -----------------------
import pandas as pd
import glob

# setting the year of interest
year = 2014

### -----------------------
# Reading in & combining all files
### -----------------------

# path to the folder containing the CSV files
folder_path = f'C:\Code\sam-generation\wind\data\capacityFactor_2014'

# get a list of all the CSV files in the folder
all_files = glob.glob(folder_path + "/*.csv")

# create an empty list to store each CSV file as a separate DataFrame
df_list = []

# loop through each file, read it into a DataFrame, and append it to the list
for filename in all_files:
    df = pd.read_csv(filename, index_col = None, header = 0, low_memory=False)
    df_list.append(df)

# concatenate all the DataFrames in the list into one big DataFrame
all_wind_data = pd.concat(df_list, axis=0, ignore_index=True)

### -----------------------
# Filtering for only missing FIDs
### -----------------------
# keeping only FIDs that have yet to run
missing_data = all_wind_data[all_wind_data['CF_status'] != 1]

### -----------------------
# Adding all FID values (if any are missing)
### -----------------------
# creating a list of all FIDs and merging with the other list - if any FIDs are missing
values = list(range(1, 3012))
df_FID_list = pd.DataFrame({'FID': values})
merged_df = pd.merge(df_FID_list, all_wind_data, on='FID', how='left')

# keeping only FIDs that have yet to run
missing_data = merged_df[merged_df['CF_status'] != "done"]

### -----------------------
# Saving the data as a csv
### -----------------------

# setting the file name and path to save
file_path_to_save = r'filepath'

# writing to a .csv file
missing_data.to_csv(file_path_to_save, index = False)
