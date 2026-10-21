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

cutting_date = "2026-06-12"
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
# Experimental fraction of rainfall retained by the hay.
# 1.0 = 100% retention; 0.5 = 50% retention.
# This is a sensitivity-test assumption, not a measured value.
rainfall_retention_fraction = 0.5
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

    # Published-style experimental rainfall response
    predicted_moisture = (
        4.0
        + (moisture_db - 4.0)
        * math.exp(-150.0 * rainfall_mm / density)
    )

    # Physical upper limit: all rainfall retained by the hay
    maximum_moisture = moisture_db + (
    rainfall_mm * 1000 * rainfall_retention_fraction / density
)

    # Do not allow more water gain than rainfall supplies
    return min(predicted_moisture, maximum_moisture)


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
         # Spread hourly rainfall across four 15-minute intervals.
        # This is an assumption, not measured 15-minute rainfall.
        hourly_rainfall = drying_hourly["precipitation"][hour_index + 1]
        moisture_before_rain = moisture_db
        if hourly_rainfall is not None and hourly_rainfall > 0:
            rainfall_15min = hourly_rainfall / 4

            moisture_db = absorb_rain(
                moisture_db,
                rainfall_15min,
                swath_density
            )
        rain_gain_db = moisture_db - moisture_before_rain

        # Experimental nighttime moisture regain.
        # Low solar radiation and high humidity are used
        # as indicators of possible dew conditions.
        moisture_before_dew = moisture_db

        if solar < 10 and humidity >= 85:
            equilibrium_db = nighttime_equilibrium_moisture(
                humidity,
                wind
            )

            # Only absorb moisture if equilibrium is higher.
            if equilibrium_db > moisture_db:
                moisture_db = absorb_dew(
                    moisture_db,
                    equilibrium_db,
                    prediction_interval_hours,
                    swath_density
                )

        dew_gain_db = moisture_db - moisture_before_dew

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
            "drying_rate": drying_rate,
            "rain_gain_db": rain_gain_db,
            "dew_gain_db": dew_gain_db
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


# STEP 11: INSPECT MOISTURE DURING JUNE 18 RAINFALL

print("\nJUNE 18 STORM MOISTURE CHECK")

for result in simulation_results:
    if (
        result["time"].date().isoformat() == "2026-06-18"
        and result["time"].minute == 0
        and 14 <= result["time"].hour <= 21
    ):
        print(
            result["time"],
            "| Moisture:",
            f"{result['moisture_percent']:.2f}%"
        )

        # STEP 12: FIND REHYDRATION FROM 5% TO 15%

print("\nREHYDRATION TO 15% CHECK")

if dehydration_time is not None:
    previous_result = None
    rehydration_result = None

    for result in simulation_results:
        if result["time"] <= dehydration_time:
            continue

        if previous_result is not None:
            if (
                previous_result["moisture_percent"] < 15.0
                and result["moisture_percent"] >= 15.0
            ):
                rehydration_result = result
                break

        previous_result = result

    if rehydration_result is not None:
        print("First predicted return to 15%:", rehydration_result["time"])
        print(
            "Predicted moisture:",
            f"{rehydration_result['moisture_percent']:.2f}%"
        )
    else:
        print("15% was not reached after dehydration during this simulation.")
else:
    print("The alfalfa did not reach 5% first.")

    # STEP 13: INSPECT THE 15% REHYDRATION CROSSING

if rehydration_result is not None:
    crossing_index = simulation_results.index(rehydration_result)

    print("\n15% REHYDRATION CROSSING DETAILS")

    for result in simulation_results[
        max(0, crossing_index - 2):crossing_index + 2
    ]:
        print(
            result["time"],
            "| Moisture:",
            f"{result['moisture_percent']:.2f}%"
        )

        # STEP 14: INVESTIGATE JUNE 18 MOISTURE REGAIN

print("\nJUNE 18 RAIN AND DEW CONTRIBUTIONS")

for result in simulation_results:
    if (
        result["time"].date().isoformat() == "2026-06-18"
        and result["time"].hour in [7, 8]
    ):
        print(
            result["time"],
            "| Rain gain:",
            round(result["rain_gain_db"], 4),
            "| Dew gain:",
            round(result["dew_gain_db"], 4)
        )

        # STEP 15: SEPARATE DRYING AND REHYDRATION WINDOWS

drying_window = []
rehydration_window = []

for i in range(1, len(simulation_results)):
    previous = simulation_results[i - 1]
    current = simulation_results[i]

    moisture = current["moisture_percent"]
    previous_moisture = previous["moisture_percent"]

    if target_moisture_min <= moisture <= target_moisture_max:

        # Drying: moisture is decreasing.
        if moisture < previous_moisture:
            drying_window.append(current)

        # Rehydration: moisture is increasing after reaching 5%.
        elif (
            dehydration_time is not None
            and current["time"] > dehydration_time
            and moisture > previous_moisture
        ):
            rehydration_window.append(current)

print("\nSEPARATE MOISTURE WINDOWS")

if drying_window:
    print("First drying-window time:", drying_window[0]["time"])
else:
    print("No drying window found.")

if rehydration_window:
    print("First rehydration-window time:", rehydration_window[0]["time"])
else:
    print("No rehydration window found.")

    # STEP 16: FARMER-FACING REHYDRATION PREDICTION

print("\nFARMER REHYDRATION FORECAST")
print("Field:", field_location)
print("Cutting date:", cutting_date)
print("Dehydration target: 5%")
print("Rehydration target: 15%")

if rehydration_result is not None:
    print("Estimated return to 15%:", rehydration_result["time"])
    print("\n15-MINUTE MOISTURE PREDICTIONS")

    crossing_index = simulation_results.index(rehydration_result)

    for result in simulation_results[
        max(0, crossing_index - 4):crossing_index + 3
    ]:
        print(
            result["time"].strftime("%Y-%m-%d %I:%M %p"),
            "| Estimated moisture:",
            f"{result['moisture_percent']:.2f}%"
        )
else:
    print("No return to 15% predicted during this period.")

print("\nWARNING: Experimental prediction.")
print("Check actual hay moisture and field conditions before baling.")