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

# Farmer-provided information

field_location = "Weatherford, Oklahoma"
cutting_date = "2026-10-01"
cutting_time = "09:00"
crop_type = "alfalfa"


print("Hay Moisture Estimator")
print("Field Location:", field_location)
print("Cutting Date:", cutting_date)
print("Cutting Time:", cutting_time)
print("Crop Type:", crop_type)

# Step 1: Collect historical weather data

latitude = 35.5262
longitude = -98.7076

weather_url = "https://archive-api.open-meteo.com/v1/archive"

# Weather data needed before cutting

weather_parameters = {
    "latitude": latitude,
    "longitude": longitude,
    "start_date": "2026-09-24",
    "end_date": "2026-09-30",
    "daily": [
        "precipitation_sum",
        "et0_fao_evapotranspiration"
    ],
    "timezone": "America/Chicago"
}

# Send the request to Open-Meteo
response = requests.get(
    weather_url,
    params=weather_parameters,
    timeout=60
)

# Check if the request was successful
response.raise_for_status()

# Convert the response into Python data
weather_data = response.json()

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
