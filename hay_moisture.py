# Alfalfa Hay Drying and Baling Time Estimator
# Master's Practicum Project
# University of Oklahoma 

# Project Purpose:
# Develop a web-based application that will help farmers
# estimate when their alfalfa hay will be ready to bale. 
# The application will use farmer-provided information, 
# weather data, intitial moisture estimation, and the
# Rotz dryign model to predict a baling time. 

import requests
import json
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import math
import os
import time
from datetime import datetime

# Retrieve weather data with retries and a saved backup
def get_weather_data(url, parameters, filename):

    # Check whether saved data matches the current request
    request_info = {
        "url": url,
        "parameters": parameters
    }

    # Try the weather API up to three times
    for attempt in range(3):
        try:
            response = requests.get(
                url,
                params=parameters,
                timeout=(10, 45)
            )

            response.raise_for_status()
            data = response.json()

            # Save the successful response with its request details
            saved_data = {
                "request": request_info,
                "weather": data,
                "saved_at": datetime.now().isoformat()
            }

            temporary_file = filename + ".tmp"

            with open(temporary_file, "w") as file:
                json.dump(saved_data, file)

            os.replace(temporary_file, filename)

            print("Fresh weather data collected successfully.")
            return data

        except (requests.exceptions.RequestException, ValueError) as error:
            print(f"Weather API attempt {attempt + 1} failed: {error}")

            if attempt < 2:
                time.sleep(2 * (attempt + 1))

    # Use saved data only if it matches the current request
    if os.path.exists(filename):

        with open(filename, "r") as file:
            saved_data = json.load(file)

        if saved_data.get("request") == request_info:
            print("WARNING: Using previously saved weather data.")
            print("Saved at:", saved_data.get("saved_at"))
            return saved_data["weather"]

    raise RuntimeError(
        "Weather API unavailable and no matching saved data exists."
    )

# Farmer-provided information

field_location = "Hammon, Oklahoma"
cutting_date = "2026-10-01"
cutting_time = "09:00"
crop_type = "alfalfa"

# Farmer-provided information for swath density

hay_yield_tons_per_acre = 2.0
mower_width_feet = 16.0
swath_width_feet = 5.0

# Convert the cutting date into a date Python can calculate with
cutting_date_obj = datetime.strptime(cutting_date, "%Y-%m-%d").date()

# Calculate seven days of weather data before cutting
seven_day_start = cutting_date_obj - timedelta(days=7)
seven_day_end = cutting_date_obj - timedelta(days=1)

# Calculate the first three days of drying after cutting
drying_start = cutting_date_obj
drying_end = cutting_date_obj + timedelta(days=2)

# Calculate 30 days before and after cutting
exploration_start = cutting_date_obj - timedelta(days=30)
exploration_end = cutting_date_obj + timedelta(days=30)
# Do not request historical weather data from future dates
today = datetime.now().date()

if exploration_end >= today:
    exploration_end = today - timedelta(days=1)

print("Hay Moisture Estimator")
print("Field Location:", field_location)
print("Cutting Date:", cutting_date)
print("Cutting Time:", cutting_time)
print("Crop Type:", crop_type)

# Step 1: Collect historical weather data

latitude = 35.6328
longitude = -99.3815
# USDA soil survey estimate for Port silt loam
# Soil map unit: 384778
soil_bulk_density = 1.43  # g/cm³

weather_url = "https://archive-api.open-meteo.com/v1/archive"

# Weather data needed before cutting


weather_parameters = {
    "latitude": latitude,
    "longitude": longitude,
    "start_date": seven_day_start.isoformat(),
    "end_date": seven_day_end.isoformat(),
    "daily": [
        "precipitation_sum",
        "et0_fao_evapotranspiration"
    ],
    "hourly": [
    "soil_moisture_0_to_7cm",
    "temperature_2m",
    "relative_humidity_2m"
],

    "timezone": "America/Chicago"
}


# Collect seven-day weather data with retries and backup
weather_data = get_weather_data(
    weather_url,
    weather_parameters,
    "seven_day_weather_cache.json"
)



# Display the daily weather information
print("\nHistorical Weather Data:")
print(weather_data["daily"])

# Step 2: Calculate the seven-day water balance

# Get daily precipitation and evapotranspiration
precipitation = weather_data["daily"]["precipitation_sum"]
evapotranspiration = weather_data["daily"]["et0_fao_evapotranspiration"]

# Add the daily values together
total_precipitation = sum(precipitation)
total_evapotranspiration = sum(evapotranspiration)

# Calculate the seven-day water balance
water_balance = total_precipitation - total_evapotranspiration

# Display the results
print("\nSeven-Day Water Balance:")
print("Total Precipitation:", round(total_precipitation, 2), "mm")
print("Total Evapotranspiration:", round(total_evapotranspiration, 2), "mm")
print("Water Balance:", round(water_balance, 2), "mm")

# Step 3: Retrieve soil moisture data
# Check that the API returned the data needed for VPD
required_variables = ["temperature_2m", "relative_humidity_2m"]

for variable in required_variables:
    if variable not in weather_data["hourly"]:
        raise ValueError(
            f"Missing {variable} in weather data. "
            "Refresh the saved weather data from Open-Meteo."
        )
# Get hourly soil moisture values from the weather API
soil_moisture = weather_data["hourly"]["soil_moisture_0_to_7cm"]
# Get hourly temperature and humidity readings
hourly_temperature = weather_data["hourly"]["temperature_2m"]

hourly_humidity = weather_data["hourly"]["relative_humidity_2m"]
# Step 11: Calculate hourly Vapor Pressure Deficit (VPD)

vpd_values = []

for temperature, humidity in zip(hourly_temperature, hourly_humidity):

    saturation_vapor_pressure = 0.6108 * math.exp(
        (17.27 * temperature) / (temperature + 237.3)
    )

    vpd = saturation_vapor_pressure * (1 - humidity / 100)

    vpd_values.append(vpd)

average_vpd = sum(vpd_values) / len(vpd_values)

print("\nAverage Seven-Day VPD:")
print(round(average_vpd, 3), "kPa")

# Display the soil moisture values
print("\nSoil moisture data retrieved successfully.")
print("Number of hourly readings:", len(soil_moisture))


# Calculate the average soil moisture over seven days

# Remove any missing values
valid_soil_moisture = [
    value for value in soil_moisture if value is not None
]

# Calculate the average
average_soil_moisture = (
    sum(valid_soil_moisture) / len(valid_soil_moisture)
)

# Display the average
print("\nAverage Seven-Day Soil Moisture:")
print(round(average_soil_moisture, 4), "m³/m³")

# Step 4: Create a soil moisture time-series graph

# Get the dates and times for each hourly reading
soil_moisture_times = weather_data["hourly"]["time"]
# Plot the hourly soil moisture readings
plt.figure(figsize=(12, 6))

plt.plot(soil_moisture_times, soil_moisture)

plt.title("Seven-Day Soil Moisture")
plt.xlabel("Date and Time")
plt.ylabel("Soil Moisture (m³/m³)")

plt.xticks(range(0, len(soil_moisture_times), 24),
           soil_moisture_times[::24], rotation=45)
plt.tight_layout()

plt.savefig("soil_moisture_graph.png")
plt.close()

# Step 5: Collect weather data for exploration

exploration_parameters = {
    "latitude": latitude,
    "longitude": longitude,
    "start_date": exploration_start.isoformat(),
    "end_date": exploration_end.isoformat(),
    "daily": [
        "precipitation_sum",
        "temperature_2m_max",
        "temperature_2m_min",
        "et0_fao_evapotranspiration"
    ],
    "hourly": [
        "soil_moisture_0_to_7cm",
        "relative_humidity_2m"
    ],
    "timezone": "America/Chicago"
}
# Collect exploration weather data with retries and backup
exploration_data = get_weather_data(
    weather_url,
    exploration_parameters,
    "exploration_weather_cache.json"
)

print("\nExploration weather data is ready.")
print("Number of daily readings:", len(exploration_data["daily"]["time"]))
print("Number of hourly readings:", len(exploration_data["hourly"]["time"]))


# Step 6: Graph soil moisture during the exploration period

exploration_times = exploration_data["hourly"]["time"]
exploration_soil_moisture = exploration_data["hourly"]["soil_moisture_0_to_7cm"]

plt.figure(figsize=(12, 6))

plt.plot(exploration_times, exploration_soil_moisture)
# Mark the date when the alfalfa was cut
cutting_timestamp = cutting_date + "T" + cutting_time

plt.axvline(
    x=cutting_timestamp,
    color="red",
    linestyle="--",
    label="Alfalfa Cutting Date"
)

plt.legend()

plt.title("Soil Moisture Around Alfalfa Cutting Date")
plt.xlabel("Date")
plt.ylabel("Soil Moisture (m³/m³)")

plt.xticks(
    range(0, len(exploration_times), 120),
    exploration_times[::120],
    rotation=45
)

plt.tight_layout()
plt.savefig("exploration_soil_moisture.png")
plt.close()

print("Extended soil moisture graph saved successfully.")

# Step 7: Create a precipitation graph

# Get daily dates and precipitation measurements
rainfall_dates = exploration_data["daily"]["time"]
rainfall_amounts = exploration_data["daily"]["precipitation_sum"]
# Create the precipitation bar graph
plt.figure(figsize=(12, 6))

plt.bar(rainfall_dates, rainfall_amounts, color="skyblue")
# Mark the alfalfa cutting date
plt.axvline(
    x=cutting_date,
    color="red",
    linestyle="--",
    label="Alfalfa Cutting Date"
)

plt.legend()

plt.title("Daily Precipitation Around Alfalfa Cutting Date")
plt.xlabel("Date")
plt.ylabel("Precipitation (mm)")

plt.xticks(
    range(0, len(rainfall_dates), 5),
    rainfall_dates[::5],
    rotation=45
)

plt.tight_layout()
plt.savefig("exploration_precipitation.png")
plt.close()

print("Precipitation graph saved successfully.")

# Step 8: Create a temperature graph

# Get daily temperature data from Open-Meteo
temperature_dates = exploration_data["daily"]["time"]

high_temperatures = exploration_data["daily"]["temperature_2m_max"]

low_temperatures = exploration_data["daily"]["temperature_2m_min"]
# Create the temperature graph
plt.figure(figsize=(12, 6))

# Plot daily high and low temperatures
plt.plot(temperature_dates, high_temperatures,
         color="orange", label="High Temperature")

plt.plot(temperature_dates, low_temperatures,
         color="blue", label="Low Temperature")

# Mark the alfalfa cutting date
plt.axvline(
    x=cutting_date,
    color="red",
    linestyle="--",
    label="Alfalfa Cutting Date"
)

# Add graph labels
plt.title("Daily Temperatures Around Alfalfa Cutting Date")
plt.xlabel("Date")
plt.ylabel("Temperature (°C)")

plt.xticks(
    range(0, len(temperature_dates), 5),
    temperature_dates[::5],
    rotation=45
)

plt.legend()
plt.tight_layout()

# Save the graph
plt.savefig("exploration_temperature.png")
plt.close()

print("Temperature graph saved successfully.")
# Step 9: Create a relative humidity graph

# Get hourly humidity data from Open-Meteo
humidity_times = exploration_data["hourly"]["time"]

relative_humidity = exploration_data["hourly"]["relative_humidity_2m"]

# Create the relative humidity graph
plt.figure(figsize=(12, 6))

# Plot hourly relative humidity
plt.plot(humidity_times, relative_humidity,
         color="purple", label="Relative Humidity")

# Mark the alfalfa cutting date
cutting_timestamp = cutting_date + "T" + cutting_time

plt.axvline(
    x=cutting_timestamp,
    color="red",
    linestyle="--",
    label="Alfalfa Cutting Date"
)

# Add graph labels
plt.title("Relative Humidity Around Alfalfa Cutting Date")
plt.xlabel("Date")
plt.ylabel("Relative Humidity (%)")

plt.xticks(
    range(0, len(humidity_times), 120),
    humidity_times[::120],
    rotation=45
)

plt.legend()
plt.tight_layout()

# Save the graph
plt.savefig("exploration_humidity.png")
plt.close()

print("Relative humidity graph saved successfully.")

# Step 10: Create an evapotranspiration graph

# Get daily evapotranspiration data from Open-Meteo
et_dates = exploration_data["daily"]["time"]

evapotranspiration = exploration_data["daily"]["et0_fao_evapotranspiration"]
# Create the evapotranspiration graph
plt.figure(figsize=(12, 6))

# Plot daily reference evapotranspiration
plt.plot(et_dates, evapotranspiration,
         color="green", label="Reference Evapotranspiration")

# Mark the alfalfa cutting date
plt.axvline(
    x=cutting_date,
    color="red",
    linestyle="--",
    label="Alfalfa Cutting Date"
)

# Add graph labels
plt.title("Daily Evapotranspiration Around Alfalfa Cutting Date")
plt.xlabel("Date")
plt.ylabel("Reference Evapotranspiration (mm/day)")

plt.xticks(
    range(0, len(et_dates), 5),
    et_dates[::5],
    rotation=45
)

plt.legend()
plt.tight_layout()

# Save the graph
plt.savefig("exploration_evapotranspiration.png")
plt.close()

print("Evapotranspiration graph saved successfully.")
# Step 12: Prepare weather measurements for the Hydration Index

# Store our three calculated weather measurements
soil_moisture_value = average_soil_moisture
water_balance_value = water_balance
vpd_value = average_vpd

print("\nWeather Measurements for Hydration Index:")
print("Soil Moisture:", round(soil_moisture_value, 4), "m³/m³")
print("Water Balance:", round(water_balance_value, 2), "mm")
print("Average VPD:", round(vpd_value, 3), "kPa")
# Step 13: Normalize soil moisture

# Temporary reference values for testing
soil_moisture_min = 0.10
soil_moisture_max = 0.40

# Calculate normalized soil moisture
normalized_soil_moisture = (
    (soil_moisture_value - soil_moisture_min)
    / (soil_moisture_max - soil_moisture_min)
)

# Keep the normalized value between 0 and 1
normalized_soil_moisture = max(
    0, min(1, normalized_soil_moisture)
)

print("\nNormalized Soil Moisture:")
print(round(normalized_soil_moisture, 4))
# Step 14: Normalize seven-day water balance

# Temporary reference values for testing
water_balance_min = -50
water_balance_max = 50

# Calculate normalized water balance
normalized_water_balance = (
    (water_balance_value - water_balance_min)
    / (water_balance_max - water_balance_min)
)

# Keep the normalized value between 0 and 1
normalized_water_balance = max(
    0, min(1, normalized_water_balance)
)

print("\nNormalized Water Balance:")
print(round(normalized_water_balance, 4))
# Step 15: Normalize Vapor Pressure Deficit (VPD)

# Temporary reference values for testing
vpd_min = 0
vpd_max = 3

# Calculate normalized VPD
normalized_vpd = (
    (vpd_value - vpd_min)
    / (vpd_max - vpd_min)
)

# Keep normalized VPD between 0 and 1
normalized_vpd = max(0, min(1, normalized_vpd))

# Reverse the VPD score for the Hydration Index
vpd_hydration_score = 1 - normalized_vpd

print("\nNormalized VPD:")
print(round(normalized_vpd, 4))

print("VPD Hydration Score:")
print(round(vpd_hydration_score, 4))
# Step 16: Calculate the Pre-Harvest Hydration Index

# Temporary equal weights for testing
weight_soil_moisture = 1 / 3
weight_water_balance = 1 / 3
weight_vpd = 1 / 3

# Combine the three normalized weather measurements
hydration_index = (
    weight_soil_moisture * normalized_soil_moisture
    + weight_water_balance * normalized_water_balance
    + weight_vpd * vpd_hydration_score
)

print("\nPre-Harvest Hydration Index:")
print(round(hydration_index, 4))

print(round(hydration_index, 4))
# Step 17: Estimate Initial Alfalfa Moisture

# Temporary moisture limits based on our research
moisture_min = 75
moisture_max = 80

# Convert the Hydration Index into estimated initial moisture
initial_moisture = moisture_min + hydration_index * (moisture_max - moisture_min)

# Display the estimated starting moisture
print("\nExperimental Estimated Initial Alfalfa Moisture (%):")
print(round(initial_moisture, 2))

# Step 18: Convert wet-basis moisture to dry-basis moisture

# Convert percentage to decimal
initial_moisture_decimal = initial_moisture / 100

# Calculate dry-basis moisture
initial_moisture_dry_basis = initial_moisture_decimal / (1 - initial_moisture_decimal)

# Display the result
print("\nExperimental Initial Moisture (Dry Basis):")
print(round(initial_moisture_dry_basis, 4))

# Step 19: Set up hourly weather data for the Rotz drying model

drying_weather_parameters = {
    "latitude": latitude,
    "longitude": longitude,
    "start_date": drying_start.isoformat(),
    "end_date": drying_end.isoformat(),
    "hourly": [
        "shortwave_radiation",
        "temperature_2m",
        "soil_moisture_0_to_7cm",
        "relative_humidity_2m",
        "wind_speed_10m",
        "precipitation"
    ],
    "timezone": "America/Chicago"
}
# Step 20: Retrieve hourly weather data for drying

drying_weather_data = get_weather_data(
    weather_url,
    drying_weather_parameters,
    "drying_weather_cache.json"
)

print("\nHourly drying weather data collected successfully.")

# Step 21: Check the hourly drying weather data

drying_hourly = drying_weather_data["hourly"]

print("\nNumber of hourly drying readings:")
print(len(drying_hourly["time"]))

print("\nFirst hourly weather reading:")
print("Time:", drying_hourly["time"][0])
print("Solar Radiation:", drying_hourly["shortwave_radiation"][0], "W/m²")
print("Temperature:", drying_hourly["temperature_2m"][0], "°C")
print("Soil Moisture:", drying_hourly["soil_moisture_0_to_7cm"][0], "m³/m³")

# Step 22: Find the first hourly reading at cutting time

cutting_datetime = f"{cutting_date}T{cutting_time}"

cutting_hour_index = drying_hourly["time"].index(cutting_datetime)

print("\nCutting Date and Time:")
print(cutting_datetime)

print("\nFirst Drying Weather Reading:")
print("Time:", drying_hourly["time"][cutting_hour_index])
print("Solar Radiation:", drying_hourly["shortwave_radiation"][cutting_hour_index], "W/m²")
print("Temperature:", drying_hourly["temperature_2m"][cutting_hour_index], "°C")
print("Soil Moisture:", drying_hourly["soil_moisture_0_to_7cm"][cutting_hour_index], "m³/m³")

# Step 23: Prepare weather variables for the Rotz drying model

# Solar radiation at cutting time
SI = drying_hourly["shortwave_radiation"][cutting_hour_index]

# Air temperature at cutting time
DB = drying_hourly["temperature_2m"][cutting_hour_index]

# Soil moisture at cutting time
SM = drying_hourly["soil_moisture_0_to_7cm"][cutting_hour_index]

print("\nRotz Weather Variables at Cutting:")
print("SI (Solar Radiation):", SI)
print("DB (Air Temperature):", DB)
print("SM (Soil Moisture):", SM)
# Step 24: Calculate swath density

# Convert dry-matter yield from tons/acre to grams/m²
yield_grams_per_m2 = (
    hay_yield_tons_per_acre * 907184.74 / 4046.86
)

# Account for hay being concentrated into the swath
swath_density = yield_grams_per_m2 * (
    mower_width_feet / swath_width_feet
)

# Display swath density
print("\nEstimated Swath Density (g/m²):")
print(round(swath_density, 2))
# Step 25: Determine whether drying is on the cutting day

current_drying_date = cutting_date_obj

if current_drying_date == cutting_date_obj:
    DAY = 1
else:
    DAY = 0

print("\nRotz First-Day Indicator:")
print(DAY)

# Step 26: Set chemical conditioning rate
# Assume no chemical drying treatment was applied
AR = 0

print("\nRotz Chemical Conditioning Rate:")
print(AR)

# Step 27: Convert soil moisture to dry-basis percentage

# Open-Meteo soil moisture is in m³/m³
# USDA soil bulk density is in g/cm³

SM_dry_basis = (SM / soil_bulk_density) * 100

print("\nSoil Moisture (Dry Basis %):")
print(round(SM_dry_basis, 2))


# Step 28: Calculate the Rotz drying rate

# Use the converted soil moisture percentage
SM = SM_dry_basis

# Rotz and Chen (1985), Equation 5
drying_rate = (
    (SI * (1 + 9.30 * AR) + 5.42 * DB)
    /
    (
        66.4 * SM
        + swath_density * (2.06 - 0.97 * DAY) * (1.55 + 21.9 * AR)
        + 3037
    )
)

print("\nRotz Drying Rate (per hour):")
print(round(drying_rate, 4))

# Step 29: Predict alfalfa moisture after one hour

import math

drying_hours = 1

# Rotz and Chen (1985), Equation 2
moisture_after_one_hour_db = (
    initial_moisture_dry_basis
    * math.exp(-drying_rate * drying_hours)
)

# Convert dry-basis moisture back to wet-basis percentage
moisture_after_one_hour_wb = (
    moisture_after_one_hour_db
    / (1 + moisture_after_one_hour_db)
) * 100

print("\nPredicted Alfalfa Moisture After One Hour (%):")
print(round(moisture_after_one_hour_wb, 2))

print("\nMoisture Calculation Check:")
print("Initial Moisture (%):", initial_moisture)
print("Initial Moisture (Dry Basis):", initial_moisture_dry_basis)
print("Drying Rate:", drying_rate)

# Step 30: Display a summary of our first drying prediction

print("\n--- HAY DRYING PREDICTION SUMMARY ---")
print("Field Location:", field_location)
print("Cutting Date:", cutting_date)
print("Cutting Time:", cutting_time)
print("Starting Moisture (%):", round(initial_moisture, 2))
print("Drying Rate (per hour):", round(drying_rate, 4))
print("Moisture After One Hour (%):", round(moisture_after_one_hour_wb, 2))
# Step 31: Display the first five drying hours

print("\nFirst Five Drying Hours:")

for i in range(cutting_hour_index, cutting_hour_index + 5):
    print(drying_hourly["time"][i])

    # Step 32: Set up 15-minute moisture prediction intervals

prediction_interval_minutes = 15

# Convert minutes into hours for the Rotz equation
prediction_interval_hours = prediction_interval_minutes / 60

# Number of predictions in one day
predictions_per_day = int(24 / prediction_interval_hours)

print("\n15-Minute Prediction Settings:")
print("Prediction interval:", prediction_interval_minutes, "minutes")
print("Time step in hours:", prediction_interval_hours)
print("Predictions per day:", predictions_per_day)

# Step 33: Calculate moisture every 15 minutes for the first hour

current_moisture_db = initial_moisture_dry_basis

print("\nFirst Hour: 15-Minute Moisture Predictions")

for step in range(1, 5):

    # Apply the Rotz drying rate over 15 minutes
    current_moisture_db = (
        current_moisture_db
        * math.exp(-drying_rate * prediction_interval_hours)
    )

    # Convert dry-basis moisture to wet-basis percentage
    current_moisture_wb = (
        current_moisture_db / (1 + current_moisture_db)
    ) * 100

    elapsed_minutes = step * prediction_interval_minutes

    print(
        f"After {elapsed_minutes} minutes:",
        f"{current_moisture_wb:.2f}%"
    )

    # Step 34: Examine changing hourly drying conditions

print("\nHourly Weather Conditions After Cutting:")

for i in range(cutting_hour_index, cutting_hour_index + 5):

    weather_time = drying_hourly["time"][i]
    solar = drying_hourly["shortwave_radiation"][i]
    temperature = drying_hourly["temperature_2m"][i]
    soil_moisture = drying_hourly["soil_moisture_0_to_7cm"][i]

    print(
        f"{weather_time} | "
        f"Solar: {solar} W/m² | "
        f"Temperature: {temperature} °C | "
        f"Soil Moisture: {soil_moisture} m³/m³"
    )

    # Step 35: Estimate weather conditions every 15 minutes

print("\nInterpolated Weather for the First Hour:")

start_index = cutting_hour_index

for step in range(4):

    fraction = step * prediction_interval_hours

    solar_start = drying_hourly["shortwave_radiation"][start_index]
    solar_end = drying_hourly["shortwave_radiation"][start_index + 1]

    temp_start = drying_hourly["temperature_2m"][start_index]
    temp_end = drying_hourly["temperature_2m"][start_index + 1]

    soil_start = drying_hourly["soil_moisture_0_to_7cm"][start_index]
    soil_end = drying_hourly["soil_moisture_0_to_7cm"][start_index + 1]

    solar_15min = solar_start + fraction * (solar_end - solar_start)
    temp_15min = temp_start + fraction * (temp_end - temp_start)
    soil_15min = soil_start + fraction * (soil_end - soil_start)

    elapsed_minutes = step * prediction_interval_minutes

    print(
        f"After {elapsed_minutes} minutes | "
        f"Solar: {solar_15min:.2f} W/m² | "
        f"Temperature: {temp_15min:.2f} °C | "
        f"Soil Moisture: {soil_15min:.4f} m³/m³"
    )

    # Step 36: Recalculate the Rotz drying rate every 15 minutes

print("\n15-Minute Rotz Drying Rates:")

for step in range(4):

    fraction = step * prediction_interval_hours

    # Get hourly weather measurements
    solar_start = drying_hourly["shortwave_radiation"][start_index]
    solar_end = drying_hourly["shortwave_radiation"][start_index + 1]

    temp_start = drying_hourly["temperature_2m"][start_index]
    temp_end = drying_hourly["temperature_2m"][start_index + 1]

    soil_start = drying_hourly["soil_moisture_0_to_7cm"][start_index]
    soil_end = drying_hourly["soil_moisture_0_to_7cm"][start_index + 1]

    # Interpolate weather for this 15-minute interval
    SI = solar_start + fraction * (solar_end - solar_start)
    DB = temp_start + fraction * (temp_end - temp_start)
    soil_volumetric = soil_start + fraction * (soil_end - soil_start)

    # Convert soil moisture to dry-basis percentage
    SM = (soil_volumetric / 1.43) * 100

    # Calculate Rotz drying rate
    DR = (
        SI * (1 + 9.30 * 0) + 5.42 * DB
    ) / (
        66.4 * SM
        + 1434.69 * (2.06 - 0.97 * 1) * (1.55 + 21.9 * 0)
        + 3037
    )

    elapsed_minutes = step * prediction_interval_minutes

    print(
        f"After {elapsed_minutes} minutes: "
        f"Drying rate = {DR:.5f} per hour"
    )

    # Step 37: Predict moisture using changing 15-minute drying rates

print("\nUpdated 15-Minute Moisture Predictions:")

moisture_db = initial_moisture_dry_basis

for step in range(4):

    fraction = step * prediction_interval_hours

    # Estimate weather conditions
    SI = (
        drying_hourly["shortwave_radiation"][start_index]
        + fraction * (
            drying_hourly["shortwave_radiation"][start_index + 1]
            - drying_hourly["shortwave_radiation"][start_index]
        )
    )

    DB = (
        drying_hourly["temperature_2m"][start_index]
        + fraction * (
            drying_hourly["temperature_2m"][start_index + 1]
            - drying_hourly["temperature_2m"][start_index]
        )
    )

    soil_volumetric = (
        drying_hourly["soil_moisture_0_to_7cm"][start_index]
        + fraction * (
            drying_hourly["soil_moisture_0_to_7cm"][start_index + 1]
            - drying_hourly["soil_moisture_0_to_7cm"][start_index]
        )
    )

    # Convert soil moisture to dry-basis percentage
    SM = (soil_volumetric / 1.43) * 100

    # Calculate the Rotz drying rate
    DR = (
        SI + 5.42 * DB
    ) / (
        66.4 * SM
        + 1434.69 * (2.06 - 0.97) * 1.55
        + 3037
    )

    # Update moisture for 15 minutes
    moisture_db *= math.exp(-DR * prediction_interval_hours)

    # Convert to wet-basis moisture percentage
    moisture_wb = (moisture_db / (1 + moisture_db)) * 100

    elapsed_minutes = (step + 1) * prediction_interval_minutes

    print(
        f"After {elapsed_minutes} minutes: "
        f"{moisture_wb:.2f}%"
    )

    # Step 38: Calculate moisture every 15 minutes
# across all available drying weather data

print("\nFull 15-Minute Drying Simulation:")

moisture_db = initial_moisture_dry_basis

simulation_results = []

for hour_index in range(cutting_hour_index, len(drying_hourly["time"]) - 1):

    # Identify whether this is the cutting day
    current_date = drying_hourly["time"][hour_index][:10]

    if current_date == cutting_date:
        DAY = 1
    else:
        DAY = 0

    for step in range(4):

        fraction = step * prediction_interval_hours

        # Interpolate weather conditions
        SI = (
            drying_hourly["shortwave_radiation"][hour_index]
            + fraction * (
                drying_hourly["shortwave_radiation"][hour_index + 1]
                - drying_hourly["shortwave_radiation"][hour_index]
            )
        )

        DB = (
            drying_hourly["temperature_2m"][hour_index]
            + fraction * (
                drying_hourly["temperature_2m"][hour_index + 1]
                - drying_hourly["temperature_2m"][hour_index]
            )
        )

        soil_volumetric = (
            drying_hourly["soil_moisture_0_to_7cm"][hour_index]
            + fraction * (
                drying_hourly["soil_moisture_0_to_7cm"][hour_index + 1]
                - drying_hourly["soil_moisture_0_to_7cm"][hour_index]
            )
        )

        SM = (soil_volumetric / 1.43) * 100

        # Calculate Rotz drying rate
        DR = (
            SI + 5.42 * DB
        ) / (
            66.4 * SM
            + 1434.69 * (2.06 - 0.97 * DAY) * 1.55
            + 3037
        )

        # Update moisture over the 15-minute interval
        moisture_db *= math.exp(-DR * prediction_interval_hours)

        # Convert to wet-basis percentage
        moisture_wb = (moisture_db / (1 + moisture_db)) * 100

        # Calculate elapsed time
        elapsed_hours = (
            (hour_index - cutting_hour_index)
            + (step + 1) * prediction_interval_hours
        )

        simulation_results.append({
            "elapsed_hours": elapsed_hours,
            "moisture_percent": moisture_wb,
            "drying_rate": DR
        })

# Print summary without flooding the terminal
print("Total 15-minute predictions:", len(simulation_results))

print(
    "Final predicted moisture:",
    f"{simulation_results[-1]['moisture_percent']:.2f}%"
)

print(
    "Total simulated hours:",
    f"{simulation_results[-1]['elapsed_hours']:.2f}"
)

# Step 39: Check weather data needed for moisture rebound

print("\nMoisture Rebound Weather Data Check:")

required_variables = [
    "relative_humidity_2m",
    "temperature_2m",
    "wind_speed_10m"
]

for variable in required_variables:
    if variable in drying_hourly:
        print(f"{variable}: Available")
    else:
        print(f"{variable}: Missing")

        # Step 40: Examine humidity during the drying period

print("\nHumidity and Temperature After Cutting:")

for i in range(cutting_hour_index, min(cutting_hour_index + 24, len(drying_hourly["time"]))):

    weather_time = drying_hourly["time"][i]
    humidity = drying_hourly["relative_humidity_2m"][i]
    temperature = drying_hourly["temperature_2m"][i]

    print(
        f"{weather_time} | "
        f"Humidity: {humidity}% | "
        f"Temperature: {temperature} °C"
    )

    # Step 41: Summarize humidity during the prediction period

humidity_values = drying_hourly["relative_humidity_2m"][
    cutting_hour_index:
]

valid_humidity = [
    value for value in humidity_values
    if value is not None
]

print("\nHumidity Summary After Cutting:")
print("Lowest humidity:", min(valid_humidity), "%")
print("Highest humidity:", max(valid_humidity), "%")

humid_hours = sum(
    1 for value in valid_humidity if value >= 85
)

print("Hours with humidity at least 85%:", humid_hours)

# Step 42: Check for hourly precipitation data

print("\nPrecipitation Data Check:")

if "precipitation" in drying_hourly:
    print("Hourly precipitation: Available")

    rainfall_values = drying_hourly["precipitation"]

    valid_rainfall = [
        value for value in rainfall_values
        if value is not None
    ]

    print(
        "Total precipitation:",
        round(sum(valid_rainfall), 2),
        "mm"
    )

else:
    print("Hourly precipitation: Missing")

    # Step 43: Find rainfall after the alfalfa was cut

print("\nRainfall After Cutting:")

rainfall_after_cutting = drying_hourly["precipitation"][cutting_hour_index:]
times_after_cutting = drying_hourly["time"][cutting_hour_index:]

total_rain_after_cutting = 0

for time, rainfall in zip(times_after_cutting, rainfall_after_cutting):
    if rainfall is not None and rainfall > 0:
        print(f"{time} | Rainfall: {rainfall} mm")
        total_rain_after_cutting += rainfall

print(
    "Total rainfall after cutting:",
    round(total_rain_after_cutting, 2),
    "mm"
)

# Step 44: Summarize rainfall by date after cutting

from collections import defaultdict

rainfall_by_date = defaultdict(float)

for time, rainfall in zip(times_after_cutting, rainfall_after_cutting):
    if rainfall is not None and rainfall > 0:
        date = time[:10]
        rainfall_by_date[date] += rainfall

print("\nDaily Rainfall After Cutting:")

for date, total in rainfall_by_date.items():
    print(f"{date}: {total:.2f} mm")

    # Step 45: USDA field-curing dew absorption parameter
# Source: USDA Integrated Farm System Model Reference Manual
# Equation 6.4, based on Rotz (1985)

dew_absorption_rate = -4.0

print("\nUSDA Dew Absorption Parameter:")
print("Dew absorption rate:", dew_absorption_rate, "g/m² per hour")

# Step 46: Check swath density for dew absorption

swath_density_g_m2 = 1434.69

print("\nDew Model Swath Density Check:")
print("Swath density:", swath_density_g_m2, "g dry matter/m²")

if swath_density_g_m2 > 0:
    print("Swath density is positive: OK")
else:
    print("ERROR: Swath density must be positive")

    # Step 47: Check humidity and wind inputs for dew modeling

print("\nDew Model Weather Inputs:")

for i in range(cutting_hour_index, cutting_hour_index + 5):
    time = drying_hourly["time"][i]
    humidity = drying_hourly["relative_humidity_2m"][i]
    wind = drying_hourly["wind_speed_10m"][i]

    print(
        f"{time} | "
        f"Humidity: {humidity}% | "
        f"Wind: {wind} km/h"
    )

    # Step 48: Convert wind speed from km/h to m/s

print("\nWind Speed Unit Conversion:")

for i in range(cutting_hour_index, cutting_hour_index + 5):
    time = drying_hourly["time"][i]
    wind_kmh = drying_hourly["wind_speed_10m"][i]

    wind_ms = wind_kmh / 3.6

    print(
        f"{time} | "
        f"{wind_kmh:.1f} km/h = {wind_ms:.2f} m/s"
    )

# Step 49: Examine overnight humidity and wind speed
# These hours are for inspecting weather, not proving dew occurred.

print("\nOvernight Weather Conditions:")

for i in range(cutting_hour_index, len(drying_hourly["time"])):

    time = drying_hourly["time"][i]
    hour = int(time[11:13])

    if hour >= 20 or hour < 7:

        humidity = drying_hourly["relative_humidity_2m"][i]
        wind_kmh = drying_hourly["wind_speed_10m"][i]

        if humidity is None or wind_kmh is None:
            continue

        wind_ms = wind_kmh / 3.6

        print(
            f"{time} | "
            f"Humidity: {humidity}% | "
            f"Wind: {wind_ms:.2f} m/s"
        )

        # Step 50: Calculate USDA equilibrium moisture for the first night
# USDA IFSM Reference Manual, Equation 6.5

import math

night_hours = [
    i for i, time in enumerate(drying_hourly["time"])
    if "2026-10-01T20:00" <= time <= "2026-10-02T06:00"
]

night_humidity = [
    drying_hourly["relative_humidity_2m"][i]
    for i in night_hours
]

night_wind = [
    drying_hourly["wind_speed_10m"][i] / 3.6
    for i in night_hours
]

average_rh = sum(night_humidity) / len(night_humidity) / 100
average_wind = sum(night_wind) / len(night_wind)

equilibrium_moisture_db = (
    0.4 + 3.6 / math.exp(0.2 * average_wind)
) / math.exp(2.5 * (1 - average_rh))

equilibrium_moisture_wb = (
    equilibrium_moisture_db /
    (1 + equilibrium_moisture_db)
) * 100

print("\nFirst Night Equilibrium Moisture:")
print("Average humidity:", round(average_rh * 100, 2), "%")
print("Average wind:", round(average_wind, 2), "m/s")
print("Equilibrium moisture:", round(equilibrium_moisture_wb, 2), "% wet basis")

# Step 51: Correct USDA Equation 6.5

equilibrium_moisture_db = (
    0.4
    + (3.6 / math.exp(0.2 * average_wind))
    / math.exp(2.5 * (1 - average_rh))
)

equilibrium_moisture_wb = (
    equilibrium_moisture_db /
    (1 + equilibrium_moisture_db)
) * 100

print("\nCorrected USDA Equilibrium Moisture:")
print("Dry basis:", round(equilibrium_moisture_db, 4))
print("Wet basis:", round(equilibrium_moisture_wb, 2), "%")

# Step 52: Test USDA dew absorption equation (6.4)
# Illustrative starting moisture only

starting_moisture_wb = 15.0
starting_moisture_db = starting_moisture_wb / (100 - starting_moisture_wb)

night_duration_hours = 11.0

moisture_after_dew_db = (
    equilibrium_moisture_db
    + (starting_moisture_db - equilibrium_moisture_db)
    * math.exp(
        dew_absorption_rate
        * night_duration_hours
        / swath_density_g_m2
    )
)

moisture_after_dew_wb = (
    moisture_after_dew_db / (1 + moisture_after_dew_db)
) * 100

print("\nUSDA Dew Absorption Test:")
print("Starting moisture:", starting_moisture_wb, "%")
print("Predicted morning moisture:", round(moisture_after_dew_wb, 2), "%")
print(
    "Moisture change:",
    round(moisture_after_dew_wb - starting_moisture_wb, 2),
    "percentage points"
)

# Step 53: Test sensitivity to assumed swath density

print("\nDew Absorption Sensitivity Test:")

for multiplier in [0.5, 1.0, 1.5]:

    test_density = swath_density_g_m2 * multiplier

    test_moisture_db = (
        equilibrium_moisture_db
        + (starting_moisture_db - equilibrium_moisture_db)
        * math.exp(
            dew_absorption_rate
            * night_duration_hours
            / test_density
        )
    )

    test_moisture_wb = (
        test_moisture_db / (1 + test_moisture_db)
    ) * 100

    print(
        f"Density: {test_density:.2f} g/m² | "
        f"Predicted moisture: {test_moisture_wb:.2f}%"
    )

    # Step 54: Compare equilibrium moisture for two nights

night_periods = [
    ("Night 1", "2026-10-01T20:00", "2026-10-02T06:00"),
    ("Night 2", "2026-10-02T20:00", "2026-10-03T06:00")
]

print("\nNighttime Equilibrium Moisture Comparison:")

for name, start, end in night_periods:

    indices = [
        i for i, time in enumerate(drying_hourly["time"])
        if start <= time <= end
    ]

    rh_values = [
        drying_hourly["relative_humidity_2m"][i]
        for i in indices
    ]

    wind_values = [
        drying_hourly["wind_speed_10m"][i] / 3.6
        for i in indices
    ]

    avg_rh = sum(rh_values) / len(rh_values) / 100
    avg_wind = sum(wind_values) / len(wind_values)

    equilibrium_db = (
        0.4
        + (3.6 / math.exp(0.2 * avg_wind))
        / math.exp(2.5 * (1 - avg_rh))
    )

    equilibrium_wb = (
        equilibrium_db / (1 + equilibrium_db)
    ) * 100

    print(
        f"{name} | "
        f"Humidity: {avg_rh * 100:.1f}% | "
        f"Wind: {avg_wind:.2f} m/s | "
        f"Equilibrium: {equilibrium_wb:.2f}%"
    )

    # Step 55: Compare predicted dew absorption across two nights
# Illustrative test: both nights begin at 15% moisture

print("\nNighttime Moisture Regain Comparison:")

for name, start, end in night_periods:

    indices = [
        i for i, time in enumerate(drying_hourly["time"])
        if start <= time <= end
    ]

    rh_values = [
        drying_hourly["relative_humidity_2m"][i]
        for i in indices
    ]

    wind_values = [
        drying_hourly["wind_speed_10m"][i] / 3.6
        for i in indices
    ]

    avg_rh = sum(rh_values) / len(rh_values) / 100
    avg_wind = sum(wind_values) / len(wind_values)

    equilibrium_db = (
        0.4
        + (3.6 / math.exp(0.2 * avg_wind))
        / math.exp(2.5 * (1 - avg_rh))
    )

    initial_db = 15.0 / 85.0

    predicted_db = (
        equilibrium_db
        + (initial_db - equilibrium_db)
        * math.exp(
            dew_absorption_rate
            * night_duration_hours
            / swath_density_g_m2
        )
    )

    predicted_wb = predicted_db / (1 + predicted_db) * 100

    print(
        f"{name} | "
        f"Starting: 15.00% | "
        f"Predicted: {predicted_wb:.2f}% | "
        f"Change: {predicted_wb - 15:.2f} percentage points"
    )