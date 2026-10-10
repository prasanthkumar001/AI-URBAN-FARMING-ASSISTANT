"""
Smart Weather Monitoring, Plant Microclimate Analysis, Alert Generation,
and Advanced Smart Watering Planner using Open-Meteo.
"""

import requests
from datetime import datetime, date, timedelta
import time
import hashlib
import database as db

# Default fallback coordinates (New Delhi)
DEFAULT_COORDS = {"lat": 28.6139, "lon": 77.2090, "city": "New Delhi"}

# WMO Weather Codes
WMO_CODES = {
    0: ("Clear sky", "sun"),
    1: ("Mainly clear", "sun"),
    2: ("Partly cloudy", "cloud-sun"),
    3: ("Overcast", "cloud"),
    45: ("Fog", "cloud-fog"),
    48: ("Depositing rime fog", "cloud-fog"),
    51: ("Light drizzle", "cloud-drizzle"),
    53: ("Moderate drizzle", "cloud-drizzle"),
    55: ("Dense drizzle", "cloud-rain"),
    61: ("Slight rain", "cloud-rain"),
    63: ("Moderate rain", "cloud-rain"),
    65: ("Heavy rain", "cloud-heavy-rain"),
    71: ("Slight snow", "snowflake"),
    80: ("Rain showers", "cloud-rain"),
    81: ("Moderate showers", "cloud-rain"),
    82: ("Violent rain showers", "cloud-lightning-rain"),
    95: ("Thunderstorm", "cloud-lightning"),
}

# In-memory weather cache (valid for 15 mins)
_WEATHER_CACHE = {}


def get_city_coordinates(city_name):
    """Resolve city name to coordinates using Open-Meteo Geocoding API."""
    city_name = (city_name or "").strip()
    if not city_name:
        return DEFAULT_COORDS["lat"], DEFAULT_COORDS["lon"], DEFAULT_COORDS["city"]

    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=en&format=json"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if "results" in data and len(data["results"]) > 0:
                first = data["results"][0]
                return float(first["latitude"]), float(first["longitude"]), first.get("name", city_name)
    except Exception as e:
        print(f"Geocoding error for '{city_name}': {e}")

    return DEFAULT_COORDS["lat"], DEFAULT_COORDS["lon"], city_name or DEFAULT_COORDS["city"]


def fetch_current_weather(city_name="New Delhi"):
    """
    Fetches real-time weather and 24-48h hourly forecast from Open-Meteo API.
    Returns structured climate data with live status indicator.
    """
    normalized_city = (city_name or "New Delhi").strip().lower()
    now_ts = time.time()

    # Check cache (15 mins)
    if normalized_city in _WEATHER_CACHE:
        cached_time, cached_data = _WEATHER_CACHE[normalized_city]
        if now_ts - cached_time < 900:
            cached_copy = dict(cached_data)
            cached_copy["is_cached"] = True
            return cached_copy

    lat, lon, resolved_city = get_city_coordinates(city_name)

    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m"
            f"&hourly=temperature_2m,relative_humidity_2m,precipitation,precipitation_probability,wind_speed_10m,weather_code"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max"
            f"&forecast_days=3&timezone=auto"
        )
        res = requests.get(url, timeout=7)
        if res.status_code == 200:
            data = res.json()
            curr = data.get("current", {})
            daily = data.get("daily", {})
            hourly = data.get("hourly", {})

            temp = curr.get("temperature_2m", 25.0)
            humidity = curr.get("relative_humidity_2m", 50.0)
            precip = curr.get("precipitation", 0.0)
            wind = curr.get("wind_speed_10m", 5.0)
            code = curr.get("weather_code", 0)

            desc, icon = WMO_CODES.get(code, ("Fair", "sun"))

            # Next 3 days forecast summary
            forecast_days = []
            if "time" in daily:
                for i in range(min(4, len(daily["time"]))):
                    forecast_days.append({
                        "date": daily["time"][i],
                        "max_temp": round(daily["temperature_2m_max"][i], 1) if "temperature_2m_max" in daily else temp,
                        "min_temp": round(daily["temperature_2m_min"][i], 1) if "temperature_2m_min" in daily else temp - 5,
                        "rain": round(daily["precipitation_sum"][i], 1) if "precipitation_sum" in daily else 0.0,
                        "rain_prob": daily["precipitation_probability_max"][i] if "precipitation_probability_max" in daily else 0,
                        "max_wind": round(daily["wind_speed_10m_max"][i], 1) if "wind_speed_10m_max" in daily else wind
                    })

            # Next 24-48 hours hourly forecast data
            hourly_forecast = []
            if "time" in hourly:
                # Find current index
                now_iso = datetime.now().strftime("%Y-%m-%dT%H:00")
                times = hourly["time"]
                start_idx = 0
                for idx, t in enumerate(times):
                    if t >= now_iso:
                        start_idx = idx
                        break

                # Extract next 24 to 36 hours
                for idx in range(start_idx, min(start_idx + 36, len(times))):
                    h_code = hourly["weather_code"][idx] if "weather_code" in hourly else 0
                    h_desc, h_icon = WMO_CODES.get(h_code, ("Fair", "sun"))
                    hourly_forecast.append({
                        "time": times[idx],
                        "hour": times[idx].split("T")[1][:5],
                        "date": times[idx].split("T")[0],
                        "temp": round(hourly["temperature_2m"][idx], 1),
                        "humidity": round(hourly["relative_humidity_2m"][idx], 1),
                        "rain": round(hourly["precipitation"][idx], 1),
                        "rain_prob": hourly["precipitation_probability"][idx] if "precipitation_probability" in hourly else 0,
                        "wind": round(hourly["wind_speed_10m"][idx], 1),
                        "condition": h_desc,
                        "icon": h_icon
                    })

            # Approaching rain in next 24 hours (sum of forecast rain)
            approaching_rain_24h = sum(h["rain"] for h in hourly_forecast[:24])

            result = {
                "city": resolved_city,
                "latitude": lat,
                "longitude": lon,
                "temperature": round(temp, 1),
                "humidity": round(humidity, 1),
                "precipitation": round(precip, 2),
                "wind_speed": round(wind, 1),
                "condition": desc,
                "icon": icon,
                "forecast": forecast_days,
                "hourly_forecast": hourly_forecast,
                "approaching_rain_24h": round(approaching_rain_24h, 1),
                "is_cached": False,
                "status": "live",
                "last_updated": datetime.now().strftime("%I:%M %p")
            }
            _WEATHER_CACHE[normalized_city] = (now_ts, result)
            return result
    except Exception as e:
        print(f"Open-Meteo fetch error: {e}")

    # Fallback when offline or API unreachable
    today_str = date.today().strftime("%Y-%m-%d")
    tomorrow_str = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    fallback = {
        "city": city_name or "New Delhi",
        "latitude": lat,
        "longitude": lon,
        "temperature": 27.5,
        "humidity": 48.0,
        "precipitation": 0.0,
        "wind_speed": 7.5,
        "condition": "Partly Cloudy",
        "icon": "cloud-sun",
        "forecast": [
            {"date": today_str, "max_temp": 31.0, "min_temp": 20.0, "rain": 0.0, "rain_prob": 10, "max_wind": 10.0},
            {"date": tomorrow_str, "max_temp": 32.0, "min_temp": 21.0, "rain": 0.0, "rain_prob": 15, "max_wind": 12.0}
        ],
        "hourly_forecast": [],
        "approaching_rain_24h": 0.0,
        "is_cached": False,
        "status": "offline_fallback",
        "last_updated": "Offline Estimate"
    }
    return fallback


# ==================== Plant-Specific Temperature Classification ====================

def evaluate_plant_temperature_status(plant_data, weather_data):
    """
    Evaluates current and forecast temperatures against the plant's specific preferences.
    Categorizes into:
      - 'Optimal': Conditions are suitable for the selected plant.
      - 'Minimum / Too Low': Temperature is below the plant's preferred range.
      - 'Maximum / Too High': Temperature exceeds the plant's preferred range.
    """
    curr_temp = weather_data.get("temperature", 25.0)
    
    # Retrieve plant's specific ranges
    opt_min = float(plant_data.get("preferred_temp_optimal_min") or 18.0)
    opt_max = float(plant_data.get("preferred_temp_optimal_max") or 27.0)
    abs_min = float(plant_data.get("preferred_temp_min") or 10.0)
    abs_max = float(plant_data.get("preferred_temp_max") or 35.0)

    # Forecast values for today
    forecast_days = weather_data.get("forecast", [])
    today_max = forecast_days[0]["max_temp"] if forecast_days else curr_temp + 3
    today_min = forecast_days[0]["min_temp"] if forecast_days else curr_temp - 4

    if curr_temp > abs_max or today_max > abs_max:
        status = "Maximum / Too High"
        color = "red"
        badge_class = "bg-red-100 text-red-800 border-red-300"
        icon = "fa-temperature-arrow-up"
        detail = f"Current {curr_temp}°C (forecast max {today_max}°C) exceeds heat tolerance limit of {abs_max}°C."
    elif curr_temp < abs_min or today_min < abs_min:
        status = "Minimum / Too Low"
        color = "blue"
        badge_class = "bg-blue-100 text-blue-800 border-blue-300"
        icon = "fa-temperature-arrow-down"
        detail = f"Current {curr_temp}°C (forecast min {today_min}°C) drops below cold minimum limit of {abs_min}°C."
    elif opt_min <= curr_temp <= opt_max:
        status = "Optimal"
        color = "green"
        badge_class = "bg-emerald-100 text-emerald-800 border-emerald-300"
        icon = "fa-circle-check"
        detail = f"Temperature {curr_temp}°C is within ideal growing range ({opt_min}°C - {opt_max}°C)."
    elif curr_temp > opt_max:
        status = "Maximum / Too High"
        color = "amber"
        badge_class = "bg-amber-100 text-amber-800 border-amber-300"
        icon = "fa-temperature-high"
        detail = f"Temperature {curr_temp}°C is above optimal comfort ({opt_max}°C), approaching upper limit ({abs_max}°C)."
    else:
        status = "Minimum / Too Low"
        color = "amber"
        badge_class = "bg-amber-100 text-amber-800 border-amber-300"
        icon = "fa-temperature-low"
        detail = f"Temperature {curr_temp}°C is below optimal comfort ({opt_min}°C), approaching lower limit ({abs_min}°C)."

    return {
        "status": status,
        "color": color,
        "badge_class": badge_class,
        "icon": icon,
        "detail": detail,
        "current_temp": curr_temp,
        "today_max": today_max,
        "today_min": today_min,
        "optimal_range": f"{opt_min}°C – {opt_max}°C",
        "absolute_range": f"{abs_min}°C – {abs_max}°C"
    }


# ==================== Weather Alert Generator ====================

def generate_weather_alerts(user_id, plants, weather_data):
    """
    Evaluates microclimate threats against each plant and generates structured alerts
    in the database, deduplicating alerts within a 12-hour window.
    """
    if not plants:
        return []

    curr_temp = weather_data.get("temperature", 25.0)
    humidity = weather_data.get("humidity", 50.0)
    precip = weather_data.get("precipitation", 0.0)
    wind = weather_data.get("wind_speed_10m", 5.0)
    
    forecast_days = weather_data.get("forecast", [])
    today_max = forecast_days[0]["max_temp"] if forecast_days else curr_temp + 3
    today_min = forecast_days[0]["min_temp"] if forecast_days else curr_temp - 4
    today_rain = forecast_days[0]["rain"] if forecast_days else precip
    approaching_rain = weather_data.get("approaching_rain_24h", 0.0)

    for plant in plants:
        p_name = plant["plant_name"]
        p_type = plant["plant_type"]
        p_id = plant["id"]
        loc = plant.get("location_type", "Balcony")
        
        opt_min = float(plant.get("preferred_temp_optimal_min") or 18.0)
        opt_max = float(plant.get("preferred_temp_optimal_max") or 27.0)
        abs_min = float(plant.get("preferred_temp_min") or 10.0)
        abs_max = float(plant.get("preferred_temp_max") or 35.0)
        pref_range_str = f"Preferred: {opt_min}°C - {opt_max}°C (Limits: {abs_min}°C - {abs_max}°C)"

        # 1. Excessive Heat Stress Alert
        if today_max >= abs_max or curr_temp >= abs_max:
            severity = "Critical" if (today_max > abs_max + 2 or curr_temp > abs_max) else "Warning"
            dedup_str = f"{user_id}_{p_id}_heat_{date.today().strftime('%Y%m%d')}"
            h_hash = hashlib.md5(dedup_str.encode()).hexdigest()
            db.create_weather_alert(
                user_id=user_id,
                plant_id=p_id,
                severity=severity,
                alert_type="Excessive Heat",
                affected_name=f"{p_name} ({p_type})",
                weather_value=f"Forecast Max: {today_max}°C (Current: {curr_temp}°C)",
                preferred_range=pref_range_str,
                explanation=f"Extreme ambient heat may cause blossom drop, leaf curling, and severe soil dehydration in {loc.lower()} containers.",
                recommended_action="Move container plants into partial shade, mist surrounding balcony floor to raise local humidity, and avoid fertilizing during heat peaks.",
                expected_time="Midday to Late Afternoon (12:00 - 17:00)",
                dedup_hash=h_hash
            )

        # 2. Low Temperature / Cold Shock Alert
        elif today_min <= abs_min or curr_temp <= abs_min:
            severity = "Critical" if today_min < abs_min - 2 else "Warning"
            dedup_str = f"{user_id}_{p_id}_cold_{date.today().strftime('%Y%m%d')}"
            h_hash = hashlib.md5(dedup_str.encode()).hexdigest()
            db.create_weather_alert(
                user_id=user_id,
                plant_id=p_id,
                severity=severity,
                alert_type="Low Temperature",
                affected_name=f"{p_name} ({p_type})",
                weather_value=f"Forecast Min: {today_min}°C (Current: {curr_temp}°C)",
                preferred_range=pref_range_str,
                explanation=f"Cold temperatures below {abs_min}°C risk stunted vegetative growth and root chilling in potted plants.",
                recommended_action="Move containers against warm interior walls, shelter with horticultural fleece, or bring indoors overnight.",
                expected_time="Overnight into Early Morning (02:00 - 07:00)",
                dedup_hash=h_hash
            )

        # 3. Heavy Rain / Waterlogging Alert
        if today_rain >= 15.0 or approaching_rain >= 20.0 or precip >= 10.0:
            dedup_str = f"{user_id}_{p_id}_heavyrain_{date.today().strftime('%Y%m%d')}"
            h_hash = hashlib.md5(dedup_str.encode()).hexdigest()
            db.create_weather_alert(
                user_id=user_id,
                plant_id=p_id,
                severity="Critical" if (today_rain > 25.0 or precip > 15.0) else "Warning",
                alert_type="Heavy Rain & Waterlogging",
                affected_name=f"{p_name} ({p_type})",
                weather_value=f"Precipitation: {max(today_rain, precip, approaching_rain)} mm",
                preferred_range="Requires well-drained aerated potting soil",
                explanation=f"Prolonged heavy rainfall can saturate potting mix, causing root suffocation and leaching essential soil nutrients.",
                recommended_action="Clear pot drainage holes, remove drip saucer trays so water flows freely, and shield young seedlings from direct downpours.",
                expected_time="Next 12–24 Hours",
                dedup_hash=h_hash
            )

        # 4. Fungal Disease Risk (High Humidity + Warm Temps)
        if humidity >= 80.0 and 20.0 <= curr_temp <= 30.0:
            dedup_str = f"{user_id}_{p_id}_fungal_{date.today().strftime('%Y%m%d')}"
            h_hash = hashlib.md5(dedup_str.encode()).hexdigest()
            db.create_weather_alert(
                user_id=user_id,
                plant_id=p_id,
                severity="Warning",
                alert_type="Fungal Pathogen Risk",
                affected_name=f"{p_name} ({p_type})",
                weather_value=f"Humidity: {humidity}% at {curr_temp}°C",
                preferred_range="Optimal relative humidity: 50% - 70%",
                explanation="High persistent atmospheric humidity combined with warm temperatures creates favorable incubation conditions for Early Blight, Late Blight, and Leaf Mold.",
                recommended_action="Ensure leaves remain dry during watering; bottom-water container pots; space containers apart to maximize airflow across foliage.",
                expected_time="Current conditions persisting throughout today",
                dedup_hash=h_hash
            )

        # 5. Strong Winds Alert (Balconies / Terraces)
        if wind >= 25.0 and loc in ["Balcony", "Terrace", "Window Box"]:
            dedup_str = f"{user_id}_{p_id}_wind_{date.today().strftime('%Y%m%d')}"
            h_hash = hashlib.md5(dedup_str.encode()).hexdigest()
            db.create_weather_alert(
                user_id=user_id,
                plant_id=p_id,
                severity="Warning",
                alert_type="Strong Wind Damage",
                affected_name=f"{p_name} ({p_type})",
                weather_value=f"Wind Speed: {wind} km/h",
                preferred_range="Sheltered gentle breeze (< 15 km/h)",
                explanation=f"Elevated terrace and balcony gusts can topple lightweight containers, snap brittle tomato branches, and accelerate leaf desiccation.",
                recommended_action="Secure stakes and ties on tomato vines; move small pots to floor level behind balcony parapets.",
                expected_time="Current gusts active today",
                dedup_hash=h_hash
            )

        # 6. Drought / Dry Container Dehydration Alert
        if curr_temp >= 32.0 and humidity <= 35.0 and today_rain < 0.5:
            dedup_str = f"{user_id}_{p_id}_drought_{date.today().strftime('%Y%m%d')}"
            h_hash = hashlib.md5(dedup_str.encode()).hexdigest()
            db.create_weather_alert(
                user_id=user_id,
                plant_id=p_id,
                severity="Warning",
                alert_type="Extreme Dry Weather",
                affected_name=f"{p_name} ({p_type})",
                weather_value=f"Temp: {curr_temp}°C with very low humidity ({humidity}%)",
                preferred_range="Balanced microclimate",
                explanation="Hot, arid air causes rapid moisture wick from terracotta and plastic pots, leaving root balls vulnerable to dehydration shock.",
                recommended_action="Check potting mix depth. Apply organic mulch layer (straw/woodchips) to preserve root moisture.",
                expected_time="Afternoon Peak Sunshine",
                dedup_hash=h_hash
            )


# ==================== Upgraded 4-Status Smart Watering Engine ====================

def calculate_smart_watering(plant_data=None, weather_data=None, **kwargs):
    """
    Advanced urban watering planner combining:
      - Plant baseline interval
      - Growth stage multiplier (Seedling, Vegetative, Flowering/Fruiting, Mature)
      - User-recorded soil moisture (Dry, Moderate, Moist, Wet)
      - Real-time temperature & container evaporation dynamics
      - Past precipitation & approaching rain in next 24 hours

    Returns one of 4 explicit recommendations:
      1. 'Water today'
      2. 'Check soil before watering'
      3. 'Water tomorrow'
      4. 'No watering needed today'
    """
    today = date.today()

    if weather_data is None and "weather_data" in kwargs:
        weather_data = kwargs["weather_data"]
    if weather_data is None:
        weather_data = {}

    # Extract plant parameters
    if isinstance(plant_data, dict):
        p_name = plant_data.get("plant_name", "Plant")
        p_type = plant_data.get("plant_type", "Tomato").lower()
        base_days = plant_data.get("base_watering_days") or 2
        last_watered = plant_data.get("last_watered_date")
        growth_stage = plant_data.get("growth_stage", "Vegetative")
        soil_moisture = (plant_data.get("soil_moisture") or "Moderate").capitalize()
        loc = plant_data.get("location_type", "Balcony").lower()
    elif plant_data is None and kwargs:
        p_name = kwargs.get("plant_name", "Plant")
        p_type = kwargs.get("plant_type", "Tomato").lower()
        base_days = kwargs.get("base_watering_days") or 2
        last_watered = kwargs.get("last_watered_date")
        growth_stage = kwargs.get("growth_stage", "Vegetative")
        soil_moisture = (kwargs.get("soil_moisture") or "Moderate").capitalize()
        loc = kwargs.get("location_type", "Balcony").lower()
    else:
        # Fallback for simple string input
        p_type = str(plant_data).lower() if plant_data else "tomato"
        p_name = kwargs.get("plant_name", "Plant")
        base_days = kwargs.get("base_watering_days", 2)
        last_watered = kwargs.get("last_watered_date")
        growth_stage = kwargs.get("growth_stage", "Vegetative")
        soil_moisture = kwargs.get("soil_moisture", "Moderate")
        loc = kwargs.get("location_type", "Balcony").lower()

    # Calculate days since last watering
    days_since = 1
    if last_watered:
        try:
            if isinstance(last_watered, str):
                d_str = last_watered.split(" ")[0].split("T")[0]
                lw_date = datetime.strptime(d_str, "%Y-%m-%d").date()
            else:
                lw_date = last_watered
            days_since = max(0, (today - lw_date).days)
        except Exception:
            days_since = 1

    # Weather parameters
    temp = weather_data.get("temperature", 25.0)
    humidity = weather_data.get("humidity", 50.0)
    current_rain = weather_data.get("precipitation", 0.0)
    approaching_rain = weather_data.get("approaching_rain_24h", 0.0)

    # 1. Start with base interval
    adjusted_interval = float(base_days)
    reasons = []

    # 2. Growth stage adjustment
    if growth_stage in ["Flowering", "Fruiting", "Flowering/Fruiting"]:
        adjusted_interval *= 0.8
        reasons.append(f"{growth_stage} stage demands high consistent hydration for flower & fruit set")
    elif growth_stage == "Seedling":
        adjusted_interval *= 0.6
        reasons.append("Seedling shallow roots require frequent, light moisture checks")
    elif growth_stage == "Mature":
        adjusted_interval *= 1.1
        reasons.append("Established root system allows deeper, slightly spaced waterings")

    # 3. Weather adjustments
    if temp >= 35.0:
        adjusted_interval -= 1.0
        reasons.append(f"Severe heat ({temp}°C) drives intense container transpiration")
    elif temp >= 30.0:
        adjusted_interval -= 0.5
        reasons.append(f"Warm weather ({temp}°C) accelerates moisture loss")
    elif temp < 18.0:
        adjusted_interval += 1.0
        reasons.append(f"Cool temperature ({temp}°C) retards evaporation")

    if humidity >= 75.0:
        adjusted_interval += 0.5
        reasons.append(f"High ambient humidity ({humidity}%) keeps potting soil damp longer")
    elif humidity <= 35.0:
        adjusted_interval -= 0.5
        reasons.append(f"Arid air ({humidity}%) rapidly wicks container moisture")

    # 4. Urban microclimate (Balconies & Terraces evaporate faster)
    if loc in ["balcony", "terrace", "window box"]:
        adjusted_interval -= 0.3
        reasons.append(f"{loc.capitalize()} breezes increase container drying rate")

    adjusted_interval = max(0.8, round(adjusted_interval, 1))

    # 5. Rain check rule (Overrides calendar schedule!)
    if current_rain >= 2.0 and loc in ["balcony", "terrace", "window box"]:
        return {
            "status": "No watering needed today",
            "badge_color": "green",
            "badge_class": "bg-emerald-100 text-emerald-800 border-emerald-300",
            "icon": "fa-circle-check",
            "rationale": f"Recent rainfall ({current_rain} mm) detected. Potting soil has received natural saturation.",
            "days_since_watered": days_since,
            "soil_moisture": soil_moisture,
            "growth_stage": growth_stage,
            "is_estimate": True
        }

    # Approaching heavy rain within 24 hours
    if approaching_rain >= 8.0 and loc in ["balcony", "terrace", "window box"]:
        return {
            "status": "Check soil before watering",
            "badge_color": "yellow",
            "badge_class": "bg-amber-100 text-amber-800 border-amber-300",
            "icon": "fa-cloud-showers-heavy",
            "rationale": f"Substantial rainfall ({approaching_rain} mm) forecast within the next 24 hours. Hold off on watering unless surface soil is completely parched.",
            "days_since_watered": days_since,
            "soil_moisture": soil_moisture,
            "growth_stage": growth_stage,
            "is_estimate": True
        }

    # 6. User-recorded soil moisture evaluation (Overrides calendar assumptions)
    if soil_moisture in ["Wet", "Saturated"]:
        return {
            "status": "No watering needed today",
            "badge_color": "green",
            "badge_class": "bg-emerald-100 text-emerald-800 border-emerald-300",
            "icon": "fa-circle-check",
            "rationale": "Soil is currently recorded as Wet/Saturated. Allowing aeration prevents root rot.",
            "days_since_watered": days_since,
            "soil_moisture": soil_moisture,
            "growth_stage": growth_stage,
            "is_estimate": True
        }

    if soil_moisture == "Dry" and days_since >= 1:
        return {
            "status": "Water today",
            "badge_color": "red",
            "badge_class": "bg-red-100 text-red-800 border-red-300",
            "icon": "fa-droplet",
            "rationale": f"Soil recorded as Dry ({days_since} day(s) since last watering). Prompt watering needed to restore root zone moisture.",
            "days_since_watered": days_since,
            "soil_moisture": soil_moisture,
            "growth_stage": growth_stage,
            "is_estimate": True
        }

    # 7. Standard schedule logic
    if days_since == 0:
        if temp >= 36.0 and loc in ["balcony", "terrace"] and p_type in ["tomato", "mint", "basil"]:
            status = "Check soil before watering"
            color = "yellow"
            badge_class = "bg-amber-100 text-amber-800 border-amber-300"
            icon = "fa-hand-holding-droplet"
            rationale = "Watered earlier today, but extreme afternoon balcony heat may warrant a topsoil moisture check."
        else:
            status = "No watering needed today"
            color = "green"
            badge_class = "bg-emerald-100 text-emerald-800 border-emerald-300"
            icon = "fa-circle-check"
            rationale = "Already watered today. Potting soil moisture is optimal."

    elif days_since >= adjusted_interval:
        status = "Water today"
        color = "red"
        badge_class = "bg-red-100 text-red-800 border-red-300"
        icon = "fa-droplet"
        rationale = f"Due for watering ({days_since} days since last drink; target interval {adjusted_interval}d). " + "; ".join(reasons)

    elif days_since >= (adjusted_interval - 0.7):
        # Approaching due date or moderate moisture
        if approaching_rain >= 3.0:
            status = "Check soil before watering"
            color = "yellow"
            badge_class = "bg-amber-100 text-amber-800 border-amber-300"
            icon = "fa-cloud-rain"
            rationale = f"Soil moisture is borderline ({days_since}d), with rain ({approaching_rain}mm) expected soon. Check soil moisture first."
        else:
            status = "Water tomorrow"
            color = "yellow"
            badge_class = "bg-amber-100 text-amber-800 border-amber-300"
            icon = "fa-clock"
            rationale = f"Soil retains adequate hydration today. Plan to water tomorrow ({adjusted_interval}d cycle). " + "; ".join(reasons)

    else:
        status = "No watering needed today"
        color = "green"
        badge_class = "bg-emerald-100 text-emerald-800 border-emerald-300"
        icon = "fa-circle-check"
        rationale = f"Potting soil moisture remains optimal ({days_since} days since watering). " + "; ".join(reasons)

    return {
        "status": status,
        "badge_color": color,
        "badge_class": badge_class,
        "icon": icon,
        "rationale": rationale,
        "days_since_watered": days_since,
        "adjusted_interval": adjusted_interval,
        "soil_moisture": soil_moisture,
        "growth_stage": growth_stage,
        "is_estimate": True
    }
