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

# Farmer-provided information

field_location = "Weatherford, Oklahoma"
cutting_date = "2026-10-01"
cutting_time = "09:00"
crop_type = "alfalfa"

# Convert the cutting date into a date Python can calculate with
cutting_date_obj = datetime.strptime(cutting_date, "%Y-%m-%d").date()

# Calculate seven days of weather data before cutting
seven_day_start = cutting_date_obj - timedelta(days=7)
seven_day_end = cutting_date_obj - timedelta(days=1)

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

latitude = 35.5262
longitude = -98.7076

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
# Try collecting exploration weather data up to three times
for attempt in range(3):
    try:
        exploration_response = requests.get(
            weather_url,
            params=exploration_parameters,
            timeout=30
        )

        exploration_response.raise_for_status()
        exploration_data = exploration_response.json()

        print("Exploration weather data collected successfully.")
        break

    except requests.exceptions.RequestException as error:
        print("Weather API attempt failed:", error)

        if attempt == 2:
            print("Could not collect exploration weather data.")
            raise

print("\nExploration weather data collected successfully.")
print("Number of daily readings:", len(exploration_data["daily"]["time"]))
print("Number of hourly readings:", len(exploration_data["hourly"]["time"]))# Request historical weather data for exploration
exploration_response = requests.get(
    weather_url,
    params=exploration_parameters,
    timeout=30
)

# Check whether the API request was successful
exploration_response.raise_for_status()

# Convert the response into Python data
exploration_data = exploration_response.json()

print("\nExploration weather data collected successfully.")
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