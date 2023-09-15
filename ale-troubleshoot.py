
## ================
## LOAD PACKAGES AND LIBRARIES
## ================

import pandas as pd
import os
import numpy as np
import shutil
import sys

from pyomo.environ import *
from pyomo.opt import SolverFactory
import cplex

import time
start_time = time.time()

current_dir = os.getcwd()
print(current_dir)

# Define input folder
inputFolder = os.path.join(current_dir, 'data')


## ================
## SET SOLVER
## ================

## installed ipopt, cbc, glpk, cplex solvers
solver = "cplex"

if solver == "cplex":
    opt = SolverFactory('cplex', executable="/Applications/CPLEX_Studio2211/cplex/bin/x86-64_osx/cplex")
    opt.options["mipgap"] = 0.005

# create a pandas dataframe with column names
output_df = pd.DataFrame(columns = ["PID", "solar_capacity", "wind_capacity", "solar_wind_ratio", "tx_capacity", "revenue", "cost", "profit"])
# create the sequence for PIDs, total 1335 PIDS
seq = list(range(1, 1336))
# add the sequence to the PID column in the df
output_df['PID'] = seq
# save the df as a csv 
# output_df.to_csv(os.path.join(inputFolder, "model_results.csv"), index=False)
# read in model_results.csv as a dataframe
output_df_path = os.path.join(inputFolder, "model_results_test.csv")
# output_df = pd.read_csv(output_df_path, engine = 'python')


## =================================================
## FUNCTION THAT RUNS OPTIMIZATION FOR A SINGLE PID
## =================================================

def runOptimization(PID):
    ## ================
    ## SET PARAMETERS
    ## ================

    print("PID: ", PID)

    ## ================
    ## SCALAR
    ## ================

    ## CAPITAL AND OPERATION & MAINTENANCE COSTS
    # Define capital expenditure for wind and solar (scalar, in USD/MW)
    capEx_w = (950+700)/2*1000 
    capEx_s = (752+618)/2*1000 
    # Define operations & maintenance costs for wind and solar (scalar, in USD/MW/yr)
    om_w = (39+34)/2*1000 
    om_s = (13+15)/2*1000 


    ## PRODUCTION TAX CREDIT
    # Define production tax credit (scalar, in USD per MWh)
    PTC_wind = 26 
    PTC_solar = 27.5 


    ## CAPITAL RECOVERY FACTOR
    # Define discount rate for capital recovery factor
    d = 0.05 
    # Define number of years for capital recovery factor
    n = 25
    # Define capital recovery factor (scalar)
    CRF = (d*(1+d)**n)/((1+d)**n - 1)


    ## TRANSMISSION AND SUBSTATION COSTS
    # Define USD2018 per km per MW for total transmission costs per MW
    i = 572843/500 #USD2018 per km for $500 MW of capacity so divide by 500 to get per MW
    # Define per MW for total transmission costs per MW
    sub = 7609776/200 ##per 200 MW so divide by 200 to get per MW
    # Define kilometers for total transmission costs per MW
    # read in file that has PIDs and corresponding distance to closest substation 115kV or higher
    pid_substation_file = os.path.join(inputFolder, "substation_pids.csv")
    pid_substation_df = pd.read_csv(pid_substation_file)
    # determine which GEA the PID entered into the function belongs to
    km = pid_substation_df.loc[pid_substation_df['PID'] == PID, 'distance_km'].values[0]
    # Define total transmission costs per MW (scalar)
    totalTx_perMW = i*km+sub ## USD per MW cost of tx + substation

    ## SOLAR AND WIND POTENTIAL INSTALLED CAPACITY
    # Set file path and read csv file for potential capacity for solar
    cap_s_path = os.path.join(inputFolder, "potentialInstalledCapacity", "solar_land_capacity.csv") #replace with land capacity file for solar
    cap_s_df = pd.read_csv(cap_s_path)
    cap_s = cap_s_df.loc[cap_s_df['PID'] == PID, 'solar_installed_cap_mw'].iloc[0]

    # Set file path and read csv file for potential capacity for wind
    cap_w_path = os.path.join(inputFolder, "potentialInstalledCapacity", "wind_land_capacity.csv") # replace with land capacity file for wind
    cap_w_df = pd.read_csv(cap_w_path)
    cap_w = cap_w_df.loc[cap_w_df['PID'] == PID, 'p_cap_mw'].iloc[0]
    
    ## ================
    ## VECTOR
    ## ================

    ## WHOLESALE ELECTRICITY PRICES
    # read in file that has PIDs and corresponding GEAs
    pid_gea_file = os.path.join(inputFolder, "US_pids_GEAs.csv")
    pid_gea_df = pd.read_csv(pid_gea_file)

    # determine which GEA the PID entered into the function belongs to
    gea = pid_gea_df.loc[pid_gea_df['PID'] == PID, 'gea'].values[0]

    # Set folder path where wholesale electricity prices are for each GEA
    ePrice_df_folder = os.path.join(inputFolder, "cashFlow_wide")

    # set path for electricity prices file for the specified GEA
    ePrice_path = ePrice_df_folder + "/cambiumHourly_" + gea + ".csv"
    ePrice_df_wind = pd.read_csv(ePrice_path)

    ## SOLAR AND WIND CAPACITY FACTORS
    cf_s_path = inputFolder + "/solarCapacityFactorFilePerPID_25years" + "/capacity_factor_PID" + str(PID) + ".csv"
    cf_s_df = pd.read_csv(cf_s_path)
    ## subset to only the capacity factor column
    # cf_only_s_df = cf_s_df.loc[:,"energy_generation"]

    cf_w_path = inputFolder + "/windCapacityFactorFilePerPID_25years" + "/capacity_factor_PID" + str(PID) + ".csv"
    cf_w_df = pd.read_csv(cf_w_path)
    ## subset to only the capacity factor column
    # cf_only_w_df = cf_w_df.loc[:,"energy_generation"]


    ## ===============
    ## FUNCTIONS for generating dictionary objects from dfs
    ## ===============

    ## FUNCTION: Create dictionary from ix1 vector: where i_indexName is the name of the index as a string, and i_indexList is a list of those index names

    def pyomoInput_dfVectorToDict(df, i_indexName, i_indexList):
    
        ## merge index list to df of vector data
        df_merged = pd.concat([pd.DataFrame({i_indexName: i_indexList}), df], axis = 1)
    
        ## set the index
        df_merged.set_index(i_indexName, inplace = True)
        return df_merged.to_dict()
    
    ## FUNCTION: Create dictionary from matrix 

    def pyomoInput_matrixToDict(infile, type, i_indexName, j_indexNames_list):
        if type == "csv":
            df = pd.read_csv(infile, sep=',')
        if type == "excel":
            df = pd.read_excel(infile)
        
        # vre_gen = vre_gen_all.loc[vre_gen_all['Day'] == 1] # Select all the rows for a particular day in the loop

        ## melt by indicies
        df_melt = pd.melt(df, id_vars = i_indexName, value_vars = j_indexNames_list)
        
        ## melted all the j_indexNames_list into "variable" column --> make this the second index
        df_melt.set_index([i_indexName, 'variable'], inplace = True)
        
        out_df = df_melt.to_dict()["value"]
        return out_df
    
    ## ================
    ## CREATE MODEL
    ## ================

    model = AbstractModel()

    ## ===============
    ## SET INDEX AS LIST
    ## ===============

    ## Extract hour index
    hour = cf_s_df.loc[:,"hour"].tolist()

    # Add hour list to model
    model.t = Set(initialize = hour)
    
    ## Set year index
    year = list(range(1, 26))
    
    ## Add year list to model
    model.y = Set(initialize = year)
    
    model.HOURYEAR = model.t * model.y

    ## ================
    ## SET VECTOR PARAMETERS AS DICTIONARIES
    ## ================

    ## ELECTRICITY PRICES ---
    # Electricity prices for wind and solar
    # ePrice_wind_hourly = next(iter(pyomoInput_dfVectorToDict(ePrice_df_wind, "hour", hour).values()))
    # ePrice_solar_hourly = next(iter(pyomoInput_dfVectorToDict(ePrice_df_wind, "hour", hour).values()))

    ## Adapted from wind_zones_v2 script
    ePrice_wind_hourly = next(iter(pyomoInput_matrixToDict(ePrice_df_wind, "csv", "hour", year)))
    ePrice_solar_hourly = next(iter(pyomoInput_matrixToDict(ePrice_df_wind, "csv", "hour", year)))

    ePrice_wind_hourly[1, year[0]]

    # Set parameter
    # model.eprice_wind = Param(model.t, default = ePrice_wind_hourly) # price of wind at each hour
    # model.eprice_solar = Param(model.t, default = ePrice_solar_hourly) # price of solar at each hour

    ## Adapted from wind_zones_v2 script
    model.eprice_wind = Param(model.HOURYEAR, default = ePrice_wind_hourly) # price of wind at each hour
    model.eprice_solar = Param(model.HOURYEAR, default = ePrice_solar_hourly) # price of solar at each hour

    ## CAPACITY FACTORS ---
    # Extract wind capacity factor as vector
    # wind_cf_hourly = next(iter(pyomoInput_dfVectorToDict(cf_only_w_df, "hour", hour).values()))
    # Set parameter
    # model.cf_wind = Param(model.t, default = wind_cf_hourly)

    # Extract solar capacity factor as vector
    # solar_cf_hourly = next(iter(pyomoInput_dfVectorToDict(cf_only_s_df, "hour", hour).values()))
    # Set parameter
    # model.cf_solar = Param(model.t, default = solar_cf_hourly)

    ## Adapted from wind_zones_v2 script
    wind_cf_hourly = next(iter(pyomoInput_matrixToDict(cf_w_df, "csv", "hour", year)))
    solar_cf_hourly = next(iter(pyomoInput_matrixToDict(cf_s_df, "csv", "hour", year)))

    model.cf_wind = Param(model.HOURYEAR, default = wind_cf_hourly)
    model.cf_solar = Param(model.HOURYEAR, default = solar_cf_hourly)


    ## ================
    ## SET SCALAR PARAMETERS
    ## ================
    model.capEx_w = Param(default=capEx_w)
    model.capEx_s = Param(default=capEx_s)
    model.om_w = Param(default=om_w)
    model.om_s = Param(default=om_s)
    model.CRF = Param(default=CRF)
    model.capEx_tx = Param(default=totalTx_perMW)
    model.pot_w = Param(default= cap_w)
    model.pot_s = Param(default= cap_s)
    # model.batt_rtEff_sqrt = Param(default = rtEfficiency_sqrt)
    # model.batt_power_cost = Param(default = battPowerCost)
    # model.batt_energy_cost = Param(default = battEnergyCost)

    ## ================
    ## SET VARIABLES
    ## ================

    # DECISION VARIABLES ---
    model.solar_capacity = Var(within = NonNegativeReals) ## NonNegativeReals or NonNegativeIntegers
    model.wind_capacity = Var(within = NonNegativeReals) 
    model.tx_capacity = Var(within = NonNegativeReals)

    # SLACK VARIABLES ---
    # Slack variable potential generation (without considering curtailment)
    # model.potentialGen = Var(model.HOURYEAR)
    model.potentialGen = Var(model.t)
    # Slack variable actual generation (considering curtailment)
    # model.actualGen = Var(model.HOURYEAR)
    model.actualGen = Var(model.t)  
    # Slack variable for hourly revenue
    model.revenue = Var()
    # Slack variable for annual costs
    model.cost = Var()
    
    # BATTERY VARIABLES ---
    ## Maximum energy storage of battery
    #model.duration_batt = Var(within=NonNegativeReals)
    ## Maximum power of battery
    #model.P_batt_max = Var(within=NonNegativeReals)
    ## Maximum energy of battery
    #model.E_batt_max = Var(within=NonNegativeReals)
    ## charging power in time t
    #model.P_char_t = Var(model.HOURYEAR)
    ## discharging power in time t
    #model.P_dischar_t = Var(model.HOURYEAR)
    ## Energy of battery in time t
    #model.E_batt_t = Var(model.HOURYEAR)
    ## Losses while charging in time t
    #model.L_char_t = Var(model.HOURYEAR)
    ## Losses while discharging in time t
    #model.L_dischar_t = Var(model.HOURYEAR)
    ## Export of electricity to grid in time t
    #model.Export_t = Var(model.HOURYEAR)

    ## ================
    ## SET OBJECTIVE FUNCTION
    ## ================

    # Define objective function: maximize profit
    def obj_rule(model):
        return model.revenue - model.cost
    model.obj = Objective(rule=obj_rule, sense = maximize)


    ## ================
    ## SET CONSTRAINTS
    ## ================

    ## Constraint (1) ---
    ## Define potential generation = equal to CF*capacity for wind and solar
    # combines both forms of generation
    def potentialGeneration_rule(model, t):
        return model.potentialGen[t] == (model.cf_solar[t, y]*model.solar_capacity + model.cf_wind[t, y] * model.wind_capacity for y in model.y)
    model.potentialGeneration = Constraint(model.t, rule=potentialGeneration_rule)

    ## Constraint (2) ---
    ## Define actual generation is less than or equal to potential generation
    # how much is actually being delivered to the grid, less than the tx constraint
    def actualGenLTEpotentialGen_rule(model, t):
        return model.actualGen[t] <= model.potentialGen[t]
    model.actualGenLTEpotentialGen = Constraint(model.t, rule = actualGenLTEpotentialGen_rule)

    ## Constraint (3) ---
    ## Define actual generation must be less than or equal to transmission capacity
    def actualGenLTEtxCapacity_rule(model, t):
        return model.actualGen[t] <= model.tx_capacity
    model.actualGenLTEtxCapacity = Constraint(model.t, rule = actualGenLTEtxCapacity_rule)

    ## Constraint (4) ---
    ## Define annual costs (equation #2)
    def lifetimeCosts_rule(model):
        return model.cost == model.solar_capacity*(model.capEx_s*model.CRF + model.om_s) + \
            model.wind_capacity*(model.capEx_w*model.CRF + model.om_w) + model.tx_capacity*(model.capEx_tx*model.CRF)
    model.annualCosts = Constraint(rule = lifetimeCosts_rule)

    ## Constraint (5) ---
    ## Ensure that capacity is less than or equal to potential for both wind and solar (equation #5)

    # Define rule for solar
    def max_capacity_solar_rule(model):
        return model.solar_capacity <= model.pot_s
    model.maxCapacity_solar = Constraint(rule=max_capacity_solar_rule)

    # Define rule for wind
    def max_capacity_wind_rule(model):
        return model.wind_capacity <= model.pot_w
    model.maxCapacity_wind = Constraint(rule=max_capacity_wind_rule)

    ## Constraint (6) ---
    ## Define annual revenue
    def lifetimeRevenue_rule(model, t):
        return model.revenue == sum(model.actualGen[t] * model.eprice_wind[t, y] for y in model.y)
    model.annualRevenue = Constraint(rule=lifetimeRevenue_rule)

    ## Constraint (7) ---
    ## Check that transmission capacity is less than wind capacity 
    # will always size tx capacity to wind capacity, never undersizes so could change tx_capacity == wind_capacity
    def tx_wind_rule(model):
        return model.tx_capacity <= model.wind_capacity #+ model.solar_capacity
    model.tx_wind = Constraint(rule=tx_wind_rule)


    ## ================
    ## RUN OPTIMIZATION
    ## ================
    model_instance = model.create_instance()
    results = opt.solve(model_instance, tee=True)
    # write out results to file named model_output.sol in working directory
    #results.write(filename='model_output.sol')

    # store variable values found in optimization
    solar_capacity = model_instance.solar_capacity.value
    wind_capacity = model_instance.wind_capacity.value
    tx_capacity = model_instance.tx_capacity.value
    revenue= model_instance.revenue.value
    cost = model_instance.cost.value
    profit = model_instance.obj()
    solar_wind_ratio = solar_capacity/wind_capacity

    output_df.loc[output_df['PID']== PID] = [PID, solar_capacity, wind_capacity, solar_wind_ratio, tx_capacity, revenue, cost, profit]


## ====================================================
## FUNCTION THAT RUNS OPTIMIZATION GIVEN A LIST OF PIDS
## ====================================================

def runOptimizationLoop(PID_list):
    i = 0 
    for PID in PID_list:
        while True:
            try: 
                i = i + 1
                #print(i)
                runOptimization(PID)
                if i == 300:
                    output_df.to_csv(output_df_path, index=False)
                    print("Saved to file")
                    i = 0
            except Exception as exc:
                print(exc)
                ## save CSV to file
                output_df.to_csv(output_df_path, index=False)
                ## PAUSE
                #time.sleep(5)
                #continue
            break  
        
    ## save CSV to file
    output_df.to_csv(output_df_path, index=False)

## ======================
## RUN OPTIMIZATION LOOP
## ======================
PID_start = 1
PID_end = PID_start + 1
start_time = time.time()
PID_list_in = list(range(PID_start,PID_end,1))
runOptimizationLoop(PID_list_in)  
end_time = time.time()
print("Time taken:", end_time - start_time, "seconds") # Print how long it takes to run the loop 
    
