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
    "hourly": [
        "soil_moisture_0_to_7cm"
    ],
    "timezone": "America/Chicago"
}



# Try to collect current data from the weather API
try:
    response = requests.get(
        weather_url,
        params=weather_parameters,
        timeout=15
    )

    response.raise_for_status()
    weather_data = response.json()

    # Save the successful response for future use
    with open("weather_data.json", "w") as file:
        json.dump(weather_data, file)

    print("Weather data collected and saved successfully.")

except requests.exceptions.RequestException as error:
    print("Weather API connection failed:", error)

    # Use previously saved weather data
    try:
        with open("weather_data.json", "r") as file:
            weather_data = json.load(file)

        print("Using previously saved weather data.")

    except FileNotFoundError:
        print("No saved weather data is available yet.")
        raise SystemExit(1)


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

# Get hourly soil moisture values from the weather API
soil_moisture = weather_data["hourly"]["soil_moisture_0_to_7cm"]

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
