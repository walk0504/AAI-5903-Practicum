# Alfalfa Hay Moisture and Baling Time Predictor
# University of Oklahoma - Master's Practicum
#
# Purpose:
# Estimate alfalfa moisture every 15 minutes and predict
# when hay may reach the farmer's desired baling range.

from datetime import datetime, timedelta
import math
import json
import os
import time
import requests
import matplotlib.pyplot as plt


# FARMER INPUTS
# These are temporary example values for testing.

field_location = "Hammon, Oklahoma"
latitude = 35.6328
longitude = -99.3815

cutting_date = "2026-06-15"
cutting_time = "08:00"

crop_type = "alfalfa"

# Field and swath information
hay_yield_tons_per_acre = 2.0
mower_width_feet = 16.0
swath_width_feet = 5.0

# Farmer's desired baling moisture range (wet basis)
target_moisture_min = 13.0
target_moisture_max = 16.0

# Prediction settings
prediction_interval_minutes = 15
prediction_interval_hours = prediction_interval_minutes / 60

# Soil information
soil_bulk_density = 1.43  # g/cm³; estimated soil value

print("\nALFALFA BALING PREDICTOR")
print("Field:", field_location)
print("Cutting:", cutting_date, cutting_time)
print(
    "Target baling moisture:",
    target_moisture_min,
    "to",
    target_moisture_max,
    "%"
)
print("Prediction interval:", prediction_interval_minutes, "minutes")
# WEATHER DATA RETRIEVAL
# Reuse the working API function from our original project.

def get_weather_data(url, parameters, filename):

    request_info = {
        "url": url,
        "parameters": parameters
    }

    # Try to retrieve fresh weather data.
    for attempt in range(3):
        try:
            response = requests.get(
                url,
                params=parameters,
                timeout=(10, 45)
            )

            response.raise_for_status()
            data = response.json()

            # Save the response for use if the API fails later.
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

    # Only use cached data when it matches the current request.
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
# STEP 3: RETRIEVE WEATHER DATA FOR THE PREDICTION

# Convert the cutting date into a Python date.
cutting_date_obj = datetime.strptime(
    cutting_date, "%Y-%m-%d"
).date()

# For now, use a three-day historical test period.
drying_start = cutting_date_obj
# Use seven days of historical weather for the test.
drying_end = cutting_date_obj + timedelta(days=6)

weather_url = "https://archive-api.open-meteo.com/v1/archive"

weather_parameters = {
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

drying_weather_data = get_weather_data(
    weather_url,
    weather_parameters,
    "drying_weather_cache.json"
)

drying_hourly = drying_weather_data["hourly"]

print("\nWEATHER DATA SUMMARY")
print("Number of hourly readings:", len(drying_hourly["time"]))
print("First reading:", drying_hourly["time"][0])
print("Last reading:", drying_hourly["time"][-1])
# STEP 4: SET EXPERIMENTAL STARTING MOISTURE
# Temporary value from our original hydration-index model.
# Not a measured or field-validated moisture reading.

initial_moisture_wb = 78.05

# Convert wet-basis percentage into dry-basis moisture ratio.
initial_moisture_db = (
    initial_moisture_wb / (100 - initial_moisture_wb)
)

# Calculate swath density using our test field inputs.
yield_grams_per_m2 = (
    hay_yield_tons_per_acre * 907184.74 / 4046.86
)

swath_density = (
    yield_grams_per_m2 * mower_width_feet / swath_width_feet
)

# Find the cutting time in our hourly weather data.
cutting_timestamp = f"{cutting_date}T{cutting_time}"

cutting_hour_index = drying_hourly["time"].index(
    cutting_timestamp
)

print("\nINITIAL MOISTURE AND FIELD SETTINGS")
print("Starting moisture:", initial_moisture_wb, "%")
print("Starting moisture (dry basis):", round(initial_moisture_db, 4))
print("Swath density:", round(swath_density, 2), "g/m²")
print("Cutting weather index:", cutting_hour_index)
# STEP 10: MOISTURE REGAIN FUNCTIONS
# These functions must be defined before Step 5 uses them.

def nighttime_equilibrium_moisture(rh_percent, wind_kmh):
    rh = rh_percent / 100
    wind_ms = wind_kmh / 3.6

    return (
        0.4
        + 3.6 / math.exp(0.2 * wind_ms)
        / math.exp(2.5 * (1 - rh))
    )


def absorb_dew(moisture_db, equilibrium_db, hours, density):
    return (
        equilibrium_db
        + (moisture_db - equilibrium_db)
        * math.exp(-4.0 * hours / density)
    )


def absorb_rain(moisture_db, rainfall_mm, density):
    return (
        4.0
        + (moisture_db - 4.0)
        * math.exp(-150.0 * rainfall_mm / density)
    )


# STEP 5: COMBINED HAY MOISTURE PREDICTION
# Rotz drying + experimental rain and nighttime moisture regain.

moisture_db = initial_moisture_db
simulation_results = []

for hour_index in range(
    cutting_hour_index,
    len(drying_hourly["time"]) - 1
):

    # Determine whether we are within the first 24 hours after cutting.
    current_hour = datetime.fromisoformat(
        drying_hourly["time"][hour_index]
    )

    cutting_datetime = datetime.fromisoformat(
        f"{cutting_date}T{cutting_time}"
    )

    hours_since_cutting = (
        current_hour - cutting_datetime
    ).total_seconds() / 3600

    DAY = 1 if hours_since_cutting < 24 else 0

    for step in range(4):
        # Your existing simulation code continues here.

        fraction = step * prediction_interval_hours

        def interpolate(variable):
            start = drying_hourly[variable][hour_index]
            end = drying_hourly[variable][hour_index + 1]
            return start + fraction * (end - start)

        solar = interpolate("shortwave_radiation")
        temperature = interpolate("temperature_2m")
        soil_moisture = interpolate("soil_moisture_0_to_7cm")
        humidity = interpolate("relative_humidity_2m")
        wind = interpolate("wind_speed_10m")

        SM = (soil_moisture / soil_bulk_density) * 100

        drying_rate = (
            solar + 5.42 * temperature
        ) / (
            66.4 * SM
            + swath_density * (2.06 - 0.97 * DAY) * 1.55
            + 3037
        )

        # Apply the Rotz drying calculation.
        moisture_db *= math.exp(
            -drying_rate * prediction_interval_hours
        )

        # Apply recorded rainfall once per hourly observation,
        # not four times for the same rainfall amount.
        if step == 3:
            rainfall = drying_hourly["precipitation"][hour_index + 1]

            if rainfall is not None and rainfall > 0:
                moisture_db = absorb_rain(
                    moisture_db,
                    rainfall,
                    swath_density
                )

        # Experimental nighttime moisture regain.
        # Low solar radiation and high humidity are used
        # as indicators of possible dew conditions.
        if solar < 10 and humidity >= 85:
            equilibrium_db = nighttime_equilibrium_moisture(
                humidity,
                wind
            )

            # Only absorb moisture when the estimated
            # equilibrium is wetter than the current hay.
            if equilibrium_db > moisture_db:
                moisture_db = absorb_dew(
                    moisture_db,
                    equilibrium_db,
                    prediction_interval_hours,
                    swath_density
                )

        moisture_wb = (
            moisture_db / (1 + moisture_db)
        ) * 100

        prediction_time = (
            datetime.fromisoformat(
                drying_hourly["time"][hour_index]
            )
            + timedelta(
                minutes=(step + 1) * prediction_interval_minutes
            )
        )

        simulation_results.append({
            "time": prediction_time,
            "moisture_percent": moisture_wb,
            "drying_rate": drying_rate
        })

print("\nCOMBINED MOISTURE PREDICTION")
print("Number of predictions:", len(simulation_results))
print(
    "Final predicted moisture:",
    f"{simulation_results[-1]['moisture_percent']:.2f}%"
)
print(
    "Final prediction time:",
    simulation_results[-1]["time"]
)


# STEP 6: IDENTIFY RAINFALL AFTER CUTTING

rainfall_events = []

for i in range(cutting_hour_index, len(drying_hourly["time"])):

    rainfall = drying_hourly["precipitation"][i]

    if rainfall is not None and rainfall > 0:
        rainfall_events.append({
            "time": drying_hourly["time"][i],
            "rainfall_mm": rainfall
        })

total_rainfall = sum(
    event["rainfall_mm"] for event in rainfall_events
)

print("\nRAINFALL DURING DRYING")
print("Rainfall events:", len(rainfall_events))
print("Total rainfall:", round(total_rainfall, 2), "mm")

for event in rainfall_events:
    print(
        event["time"],
        "|",
        event["rainfall_mm"],
        "mm"
    )
    # STEP 7: FLAG RAIN-AFFECTED PREDICTIONS
# Open-Meteo hourly precipitation is assigned to the
# preceding hour for this historical dataset.

rain_affected_intervals = 0

for result in simulation_results:

    prediction_time = result["time"]

    # Find the hourly precipitation record covering
    # the 15-minute prediction interval.
    weather_hour = prediction_time.replace(
        minute=0, second=0, microsecond=0
    )

    if prediction_time.minute > 0:
        weather_hour += timedelta(hours=1)

    weather_key = weather_hour.strftime("%Y-%m-%dT%H:%M")

    if weather_key in drying_hourly["time"]:
        index = drying_hourly["time"].index(weather_key)
        rainfall = drying_hourly["precipitation"][index]
    else:
        rainfall = None

    result["rain_affected"] = (
        rainfall is not None and rainfall > 0
    )

    if result["rain_affected"]:
        rain_affected_intervals += 1

print("\nRAINFALL IMPACT CHECK")
print("Rain-affected 15-minute intervals:", rain_affected_intervals)
print("Rainfall moisture adjustment: Applied experimentally in Step 5")


# STEP 8: FIND THE EXPERIMENTAL BALING WINDOW
# Uses combined Rotz drying and experimental rain/dew adjustments.
# Predictions below 20% moisture are outside Rotz's tested range.

baling_window = [
    result for result in simulation_results
    if target_moisture_min
    <= result["moisture_percent"]
    <= target_moisture_max
]

print("\nEXPERIMENTAL BALING WINDOW")

if baling_window:
    print("First estimated time:", baling_window[0]["time"])
    print("Last estimated time:", baling_window[-1]["time"])
    print(
        "Moisture at first estimated time:",
        f"{baling_window[0]['moisture_percent']:.2f}%"
    )
    print("Status: Experimental combined-model estimate; not yet validated.")
else:
    print("Target moisture range not reached.")
    print(
        "Final predicted moisture:",
        f"{simulation_results[-1]['moisture_percent']:.2f}%"
    )
    print("Status: More weather data or drying time may be needed.")


# STEP 9: FIND WHEN ALFALFA FIRST REACHES 5% MOISTURE

dehydration_target = 5.0

dehydration_time = None

for result in simulation_results:
    if result["moisture_percent"] <= dehydration_target:
        dehydration_time = result["time"]
        break

print("\nDEHYDRATION MILESTONE")

if dehydration_time is not None:
    print("Target moisture:", dehydration_target, "%")
    print("First predicted time at or below 5%:", dehydration_time)
else:
    print("Alfalfa did not reach 5% during the simulation.")

    