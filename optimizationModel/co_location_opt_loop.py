# -*- coding: utf-8 -*-
"""
@author: https://github.com/wattmaps
""" 

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
#current_dir should be your local path to the solar-wind-ratios folder
print(current_dir)

# Define input folder
inputFolder = os.path.join(current_dir, 'data')

## ================
## SET SOLVER
## ================

## installed ipopt, cbc, glpk, cplex solvers
solver = "cplex"

if solver == "glpk":
    opt = SolverFactory("glpk")
    
    os.environ['PATH'] = "/usr/local/bin/glpsol"
    os.environ['PATH'] = "/usr/local/bin/"

    from pyutilib.services import register_executable, registered_executable
    register_executable( name='glpsol')

if solver == "cplex":
    opt= SolverFactory('cplex', executable="/Applications/CPLEX_Studio2211/cplex/bin/x86-64_osx/cplex")
    # https://stackoverflow.com/questions/60079490/how-to-connect-cplex-and-pyomo
    # https://or.stackexchange.com/questions/4366/downloading-and-setting-up-cplex-for-pyomo
    opt.options["mipgap"] = 0.005

if solver == "glpsol": ## glpk
    if not (shutil.which("glpsol") or os.path.isfile("glpsol")):
        if "google.colab" in sys.modules:
            !apt-get install -y -qq glpk-utils
        else:
            try:
                !conda install -c conda-forge glpk 
            except:
                pass
    
    assert(shutil.which("glpsol") or os.path.isfile("glpsol"))
    opt = SolverFactory("glpsol")

if solver == "ipopt":
    assert(shutil.which("ipopt") or os.path.isfile("ipopt"))
    opt = SolverFactory("ipopt")

# create a pandas dataframe with column names
output_df = pd.DataFrame(columns=["PID", "solar_capacity", "wind_capacity", "solar_wind_ratio", "tx_capacity", "revenue", "cost", "profit"])
# create the sequence for PIDs, total 1335 PIDS
seq = list(range(1, 1336))
# add the sequence to the PID column in the df
output_df['PID'] = seq
# save the df as a csv 
#output_df.to_csv(os.path.join(inputFolder, "model_results.csv"), index=False)
# read in model_results.csv as a dataframe
output_df_path = os.path.join(inputFolder, "model_results.csv")
#output_df = pd.read_csv(output_df_path, engine = 'python')

## =================================================
## FUNCTION THAT RUNS OPTIMIZATION FOR A SINGLE PID
## =================================================

def runOptimization(PID):
    ## ================
    ## SET PARAMETERS
    ## ================

    print("PID: ", PID)
    ## CAPITAL AND O&M COSTS (SCALARS)
    # Define capital expenditure for wind and solar (scalar, in USD/MW)
    capEx_w = (950+700)/2*1000 
    capEx_s = (752+618)/2*1000 
    # Define operations & maintenance costs for wind and solar (scalar, in USD/MW/yr)
    om_w = (39+34)/2*1000 
    om_s = (13+15)/2*1000 


    ## PTC (SCALARS)
    # Define production tax credit (scalar, in USD per MWh)
    # Wind: https://windexchange.energy.gov/projects/tax-credits#:~:text=The%20Production%20Tax%20Credit%20(PTC,facility%20is%20placed%20into%20service.
    # Solar: https://www.energy.gov/eere/solar/federal-solar-tax-credits-businesses
    PTC_wind = 26 
    PTC_solar = 27.5 
    # if you set PTC to 0, results will say to not install any solar
    # recent $27/MWh federal incentive for solar


    ## CRF (SCALAR)
    # Define discount rate for capital recovery factor
    d = 0.05 
    # Define number of years for capital recovery factor
    n = 25
    # Define capital recovery factor (scalar)
    CRF = (d*(1+d)**n)/((1+d)**n - 1) # CRF = capital recovery factor, amount of money needed to pay each year over 25 years with interest


    ## TRANSMISSION AND SUBSTATION COSTS (SCALAR) #? Where did these numbers come from?
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
    #km = 7.121745 #km
    # Define total transmission costs per MW (scalar)
    totalTx_perMW = i*km+sub ## USD per MW cost of tx + substation
    
    
    ## BATTERY PARAMETERS
    rtEfficiency_sqrt = sqrt(0.85)
    
    ## batterySystemCost ($/kW) = batteryEnergyCost($/kWh)*storageDuration(h) + batteryPowerCost($/kW)

    #inputFolder_example = '/Users/michelle/Documents/UCSB Grad School/Courses/eds_411/optimization/processedData/' # used for hour_ID


    ## WHOLESALE ELECTRICITY PRICES (VECTOR)
    # read in file that has PIDs and corresponding GEAs
    pid_gea_file = os.path.join(inputFolder, "US_pids_GEAs.csv")
    pid_gea_df = pd.read_csv(pid_gea_file)

    # determine which GEA the PID entered into the function belongs to
    gea = pid_gea_df.loc[pid_gea_df['PID'] == PID, 'gea'].values[0]

    # Set folder path where wholesale electricity prices are for each GEA
    ePrice_df_folder = os.path.join(inputFolder, "cambiumHourlyPrice2030")

    # set path for electricity prices file for the specified GEA
    ePrice_path = ePrice_df_folder + "/Cambium22_Electrification_hourly_" + gea + "_2030.csv"
    
    # read in the electricity prices csv for the specified GEA and remove the top 5 rows which are not necessary
    ePrice_df = pd.read_csv(ePrice_path, skiprows=5)
    #ePrice_df.columns.values
    # Extract "total_cost_enduse" column to get prices in USD/MWh for wholesale electricity prices
    ePrice_df = ePrice_df["total_cost_enduse"]

    #to get 3 years worth of prices, repeat the total_cost_enduse data 2 more times
    ePrice_df_3_years = pd.concat([ePrice_df, ePrice_df, ePrice_df], axis = 0, ignore_index = True)

    ## WHOLESALE ELECTRICITY PRICES FOR SOLAR AND WIND(VECTOR)
    # Define wholesale electricity price for solar (vector, in USD/MWh)
    # Adding tax credit to price of solar
    ePrice_df_solar = ePrice_df_3_years+PTC_solar
    # Define wholesale electricity price for wind (vector, in USD/MWh)
    ePrice_df_wind = ePrice_df_3_years+PTC_wind 


    ## SOLAR AND WIND POTENTIAL CAPACITY (SCALAR)
    # Set file path and read csv file for potential capacity for solar
    cap_s_path = os.path.join(inputFolder, "potentialInstalledCapacity", "solar_land_capacity.csv") #replace with land capacity file for solar
    cap_s_df = pd.read_csv(cap_s_path)
    cap_s = cap_s_df.loc[cap_s_df['PID'] == PID, 'solar_installed_cap_mw'].iloc[0]

    # Set file path and read csv file for potential capacity for wind
    cap_w_path = os.path.join(inputFolder, "potentialInstalledCapacity", "wind_land_capacity.csv") # replace with land capacity file for wind
    cap_w_df = pd.read_csv(cap_w_path)
    cap_w = cap_w_df.loc[cap_w_df['PID'] == PID, 'p_cap_mw'].iloc[0]


    ## SOLAR AND WIND CAPACITY FACTORS (VECTOR)
    cf_s_path = inputFolder + "/solarCapacityFactorFilePerPID" + "/capacity_factor_PID" + str(PID) + ".csv"
    cf_s_df = pd.read_csv(cf_s_path)
    ## subset to only the capacity factor column
    cf_only_s_df = cf_s_df.loc[:,"energy_generation"]

    cf_w_path = inputFolder + "/windCapacityFactorFilePerPID" + "/capacity_factor_PID" + str(PID) + ".csv"
    cf_w_df = pd.read_csv(cf_w_path)
    ## subset to only the capacity factor column
    cf_only_w_df = cf_w_df.loc[:,"energy_generation"]


    ## Generate the large parameter that will always be greater than curtailment for creating the binary variable
    #largeVal =(cap_w + cap_s)*1.1


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
    
    ## ===============
    ## FUNCTION: Create dictionary from df (matrix)
    def pyomoInput_matrixToDict(df, i_indexName, j_indexNames_list):
            
        ## melt by indicies
        
        df_melt = pd.melt(df, id_vars=i_indexName, value_vars=j_indexNames_list)
        
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

    ## HOUR:
    hour = cf_s_df.loc[:,"hour"].tolist()

    # Add hour list to model
    model.t = Set(initialize=hour)
    
    ## YEAR index:
    year = list(range(1, 26))
    
    ## Add year list to model
    model.y = Set(initialize=year)
    
    model.HOURYEAR = Set(initialize = model.t * model.y)

    ## ================
    ## SET VECTOR PARAMETERS AS DICTIONARIES
    ## ================

    ## ELECTRICITY PRICES ---
    # electricity prices for wind and solar(vector)
    ePrice_wind_hourly = next(iter(pyomoInput_dfVectorToDict(ePrice_df_wind, "hour", hour).values()))
    ePrice_solar_hourly = next(iter(pyomoInput_dfVectorToDict(ePrice_df_solar, "hour", hour).values()))
    # set parameter
    model.eprice_wind = Param(model.t, default = ePrice_wind_hourly) # price of wind at each hour
    model.eprice_solar = Param(model.t, default = ePrice_solar_hourly) # price of solar at each hour

    ## CAPACITY FACTORS ---
    # wind cf (vector):
    wind_cf_hourly = next(iter(pyomoInput_dfVectorToDict(cf_only_w_df, "hour", hour).values()))
    # test:
    #wind_cf_hourly[1000]
    # set parameter
    model.cf_wind = Param(model.t, default = wind_cf_hourly)

    # solar cf (vector):
    solar_cf_hourly = next(iter(pyomoInput_dfVectorToDict(cf_only_s_df, "hour", hour).values()))
    # test:
    #olar_cf_hourly[1000]
    # set parameter
    model.cf_solar = Param(model.t, default = solar_cf_hourly)


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
    model.batt_rtEff_sqrt = Param(default = rtEfficiency_sqrt)
    model.batt_power_cost = Param(default = battPowerCost)
    model.batt_energy_cost = Param(default = battEnergyCost)
   

    ## ================
    ## SET VARIABLES
    ## ================

    # decision variable:
    model.solar_capacity = Var(within=NonNegativeReals) ## NonNegativeReals or NonNegativeIntegers
    model.wind_capacity = Var(within=NonNegativeReals) 
    model.tx_capacity = Var(within=NonNegativeReals)
    
    # Battery variables
    ## Maximum energy storage of battery
    model.duration_batt = Var(within=NonNegativeReals)
    ## Maximum power of battery
    model.P_batt_max = Var(within=NonNegativeReals)
    ## Maximum energy of battery
    model.E_batt_max = Var(within=NonNegativeReals)
    ## charging power in time t
    model.P_char_t = Var(model.HOURYEAR)
    ## discharging power in time t
    model.P_dischar_t = Var(model.HOURYEAR)
    ## Energy of battery in time t
    model.E_batt_t = Var(model.HOURYEAR)
    ## Losses while charging in time t
    model.L_char_t = Var(model.HOURYEAR)
    ## Losses while discharging in time t
    model.L_dischar_t = Var(model.HOURYEAR)
    ## Export of electricity to grid in time t
    model.Export_t = Var(model.HOURYEAR)

    # Slack variable potential generation (without considering curtailment)
    model.potentialGen = Var(model.HOURYEAR)
    # Slack variable actual generation (considering curtailment)
    model.actualGen = Var(model.HOURYEAR) 
    # Slack variable for hourly revenue
    model.revenue = Var()
    # Slack variable for annual costs
    model.cost = Var()


    ## ================
    ## SET OBJECTIVE FUNCTION
    ## ================

    # define objective function: maximize profit
    def obj_rule(model):
        return model.revenue - model.cost
    model.obj = Objective(rule=obj_rule, sense=maximize)


    ## ================
    ## SET CONSTRAINTS
    ## ================

    ## Constraint (1) ---
    ## Define potential generation = equal to CF*capacity for wind and solar
    # combines both forms of generation
    def potentialGeneration_rule(model, t, y):
        return model.potentialGen[t, y] == model.cf_solar[t, y]*model.solar_capacity + model.cf_wind[t,y] * model.wind_capacity
    model.potentialGeneration = Constraint(model.HOURYEAR, rule=potentialGeneration_rule)

    ## Constraint (2) ---
    ## Define actual generation is less than or equal to potential generation
    # how much is actually being delivered to the grid, less than the tx constraint
    def actualGenLTEpotentialGen_rule(model, t, y):
        return model.actualGen[t, y] <= model.potentialGen[t, y]
    model.actualGenLTEpotentialGen = Constraint(model.HOURYEAR, rule = actualGenLTEpotentialGen_rule)

    ## Constraint (3) ---
    ## Define actual generation must be less than or equal to transmission capacity
    def actualGenLTEtxCapacity_rule(model, t, y):
        return model.actualGen[t, y] <= model.tx_capacity
    model.actualGenLTEtxCapacity = Constraint(model.HOURYEAR, rule = actualGenLTEtxCapacity_rule)

    ## Constraint (4) ---
    ## Define lifetime costs (equation #2): solar or wind capEx + solar or wind fixed o&m/CRF (to get the NPV)
    def lifetimeCosts_rule(model):
        return model.cost == model.solar_capacity*model.capEx_s + model.solar_capacity*model.om_s/model.CRF + \
            model.wind_capacity*model.capEx_w + model.wind_capacity*model.om_w/model.CRF + \
                model.tx_capacity*model.capEx_tx + \
                model.P_batt_max * model.batt_power_cost + model.E_batt_max * model.batt_energy_cost
    model.annualCosts = Constraint(rule=lifetimeCosts_rule)

    ## CONSTRAINT (5) ---
    ## Ensure that capacity is less than or equal to potential for both wind and solar (equation #5)

    # Define rule for solar
    def max_capacity_solar_rule(model):
        return model.solar_capacity <= model.pot_s
    model.maxCapacity_solar = Constraint(rule=max_capacity_solar_rule)

    # Define rule for wind
    def max_capacity_wind_rule(model):
        return model.wind_capacity <= model.pot_w
    model.maxCapacity_wind = Constraint(rule=max_capacity_wind_rule)

    ## CONSTRAINT (6) ---
    ## Define annual revenue
    # taking the total generation of wind and solar and multiply by price of solar (choose price of solar or wind)
    # divide by 3 to get annual revenue when running for 3 years, get annual average revenue over 3 years
    def lifetimeRevenue_rule(model):
        return model.revenue == sum(model.Export_t[t,y]*model.eprice_wind_2030[t,y] * fraction[y] for t in model.t and y in model.y)
                    
    model.annualRevenue = Constraint(rule=lifetimeRevenue_rule)
    

    ## CONSTRAINT (7) ---
    ## Check that transmission capacity is less than wind capacity 
    # will always size tx capacity to wind capacity, never undersizes so could change tx_capacity == wind_capacity
    def tx_wind_rule(model):
        return model.tx_capacity <= model.wind_capacity #+ model.solar_capacity
    model.tx_wind = Constraint(rule=tx_wind_rule)
    
    
    ## CONSTRAINT (1 - BATTERY) ---
    ## Battery cannot simultaneously charge and discharge
    def batt_noSimultaneousChargingDischarging_rule(model, t, y):
        return model.P_char_t[t,y] * model.P_dischar_t[t,y] == 0
    model.batt_noSimultaneousChargingDischarging = Constraint(model.HOURYEAR, rule = batt_noSimultaneousChargingDischarging_rule)
    
    ## CONSTRAINT (2 - BATTERY) --- CHECK THIS!
    ## No charging in hour 1
    def batt_nochargingAtTime1_rule(model, t, y):
        return model.P_char_t[1] - model.P_dischar_t[1] == 0
    model.batt_nochargingAtTime1 = Constraint(model.HOURYEAR, rule = batt_nochargingAtTime1_rule)
    
    ## CONSTRAINT (3 - BATTERY) --- 
    ## initiate the battery charge at time  = 0 at 50% of maximum energy storage 
    def batt_startAt50percent_rule(model, t, y):
        return model.E_batt_t[1] == 0.5 * model.E_batt_max
    model.batt_startAt50percent = Constraint(model.HOURYEAR, rule = batt_startAt50percent_rule)
    
    ## CONSTRAINT (4 - BATTERY) --- 
    ## the losses while charging in hour t is equal to the charging power times 1 - the square root of the round trip efficiency
    def batt_loss_charging_rule(model, t, y):
        return model.L_char_t[t, y] == model.P_char_t[t, y] * (1 - model.batt_rtEff_sqrt)
    model.batt_loss_charging = Constraint(model.HOURYEAR, rule = batt_loss_charging_rule)
    
    ## CONSTRAINT (5 - BATTERY) --- 
    ## the losses while discharging in hour t is equal to the discharging power plus the losses while discharging times 1 - the square root of the round trip efficiency
    def batt_loss_discharging_rule(model, t, y):
        return model.L_dischar_t[t, y] == (model.P_dischar_t[t, y] + model.L_dischar_t[t, y]) * (1 - model.batt_rtEff_sqrt)
    model.batt_loss_discharging = Constraint(model.HOURYEAR, rule = batt_loss_discharging_rule)

    ## CONSTRAINT (6 - BATTERY) --- 
    ## energy balance of the battery is equal to the energy in the previous hour plus the charging power in hour t minus discharging power minus losses
    def batt_energyBalance_rule(model, t, y):
        return model.E_batt_t[t, y] == model.E_batt_t[t-1, y] + model.P_char_t[t, y] - model.P_dischar_t[t, y] - model.L_char_t[t, y] - model.L_dischar_t[t, y]
    model.batt_energyBalance = Constraint(model.HOURYEAR, rule = batt_energyBalance_rule)
    
    ## CONSTRAINT (7 - BATTERY) --- 
    ## Charge in hour t must be less than or equal to the amt of potential generation 
    def batt_chargeLessThanGeneration_rule(model, t, y):
        return -model.P_char_t[t, y] == model.potentialGen[t, y]
    model.batt_chargeLessThanGeneration = Constraint(model.HOURYEAR, rule = batt_chargeLessThanGeneration_rule)
    
    ## CONSTRAINT (8 - BATTERY) ---  
    ## Charge in hour t must be less than or equal to the amt of potential generation 
    def batt_dischargeLessThanPowerCapacity_rule(model, t, y):
        return model.P_dischar_t[t, y] <= model.P_batt_max
    model.batt_dischargeLessThanPowerCapacity = Constraint(model.HOURYEAR, rule = batt_dischargeLessThanPowerCapacity_rule)
    
    ## CONSTRAINT (9 - BATTERY) --- 
    ## Electricity exported to the grid is equal to actual generation plus the battery dicharge minus the battery charging power
    def batt_export_rule(model, t, y):
        return model.Export_t[t, y] == model.actualGen[t, y] + model.P_dischar_t[t, y] - model.P_char_t[t, y]
    model.batt_export = Constraint(model.HOURYEAR, rule = batt_export_rule)
    
    ## CONSTRAINT (10 - BATTERY) --- 
    ## Energy in battery at time t must be less than or equal to 
    def batt_export_rule(model, t, y):
        return model.Export_t[t, y] == model.actualGen[t, y] + model.P_dischar_t[t,y] - model.P_char_t[t,y]
    model.batt_chargeLessThanGeneration = Constraint(model.HOURYEAR, rule = batt_chargeLessThanGeneration_rule)
    
    
    ## CONSTRAINT (12 - BATTERY) --- 
    ## Maximum battery energy is equal to the battery duration times the maximum power of the battery
    def batt_maxEnergy_rule(model):
        return model.E_batt_max = model.P_batt_max * model.duration_batt
    model.batt_maxEnergy = Constraint(rule = batt_maxEnergy_rule)
    
    
    


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
PID_start = 168
PID_end = PID_start + 1168
start_time = time.time()
PID_list_in = list(range(PID_start,PID_end,1))
runOptimizationLoop(PID_list_in)  
end_time = time.time()
print("Time taken:", end_time - start_time, "seconds") # Print how long it takes to run the loop 