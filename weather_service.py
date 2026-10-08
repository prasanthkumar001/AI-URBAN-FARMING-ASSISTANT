"""
Smart Watering and Weather Service using Open-Meteo.
Calculates urban farming irrigation schedules factoring in crop type,
container/balcony microclimate, temperature, humidity, and rainfall.
"""

import requests
from datetime import datetime, date
import time

# Default coordinates for fallback if geocoding fails (e.g. New Delhi)
DEFAULT_COORDS = {"lat": 28.6139, "lon": 77.2090, "city": "New Delhi"}

# Plant type baseline watering intervals (in days)
PLANT_BASE_INTERVALS = {
    "tomato": 2,
    "cherry tomato": 2,
    "bell pepper": 3,
    "chilli": 3,
    "pepper": 3,
    "basil": 1,
    "mint": 1,
    "coriander": 2,
    "cilantro": 2,
    "spinach": 2,
    "lettuce": 2,
    "cucumber": 2,
    "strawberry": 2,
    "succulent": 7,
    "cactus": 8,
    "aloe vera": 7,
    "curry leaves": 3,
    "money plant": 4,
    "pothos": 4,
    "rosemary": 4,
    "eggplant": 2,
    "brinjal": 2,
    "fenugreek": 2,
    "kale": 2
}

# Weather code descriptions from WMO code table
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

# In-memory weather cache to prevent rate-limiting (keyed by city, valid for 15 minutes)
_WEATHER_CACHE = {}


def get_city_coordinates(city_name):
    """Resolve city name to latitude and longitude using Open-Meteo Geocoding API."""
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
    Fetches real-time weather data from Open-Meteo API.
    Returns structured weather dictionary.
    """
    normalized_city = city_name.strip().lower()
    now_ts = time.time()

    # Check cache (15 minutes)
    if normalized_city in _WEATHER_CACHE:
        cached_time, cached_data = _WEATHER_CACHE[normalized_city]
        if now_ts - cached_time < 900:
            return cached_data

    lat, lon, resolved_city = get_city_coordinates(city_name)

    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
            f"&timezone=auto"
        )
        res = requests.get(url, timeout=7)
        if res.status_code == 200:
            data = res.json()
            curr = data.get("current", {})
            daily = data.get("daily", {})

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
                        "max_temp": daily["temperature_2m_max"][i] if "temperature_2m_max" in daily else temp,
                        "min_temp": daily["temperature_2m_min"][i] if "temperature_2m_min" in daily else temp - 5,
                        "rain": daily["precipitation_sum"][i] if "precipitation_sum" in daily else 0.0
                    })

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
                "is_cached": False,
                "status": "success"
            }
            _WEATHER_CACHE[normalized_city] = (now_ts, result)
            return result
    except Exception as e:
        print(f"Open-Meteo fetch error: {e}")

    # Sensible fallback if offline or API unreachable
    fallback_data = {
        "city": city_name or "New Delhi",
        "latitude": lat,
        "longitude": lon,
        "temperature": 28.0,
        "humidity": 45.0,
        "precipitation": 0.0,
        "wind_speed": 8.0,
        "condition": "Warm & Clear (Simulated)",
        "icon": "sun",
        "forecast": [],
        "is_cached": False,
        "status": "offline_fallback"
    }
    return fallback_data


def calculate_smart_watering(plant_type, base_watering_days, last_watered_date, location_type, weather_data):
    """
    Computes precise watering recommendation for an urban container plant:
    Considers:
      - Plant baseline requirements
      - Real-time weather: Temperature, Humidity, Precipitation
      - Urban microclimate: Balcony/terrace container fast drying
      - Days since last watered

    Returns a dict with:
      - status: 'Water today' | 'Water tomorrow' | 'No watering needed today'
      - badge_color: 'red' | 'yellow' | 'green'
      - rationale: descriptive explanation for the urban gardener
      - days_since_watered: int
      - adjusted_interval: float
    """
    today = date.today()
    
    # Calculate days since last watering
    if last_watered_date:
        try:
            if isinstance(last_watered_date, str):
                # Try parsing YYYY-MM-DD or full timestamp
                date_part = last_watered_date.split(" ")[0].split("T")[0]
                lw_date = datetime.strptime(date_part, "%Y-%m-%d").date()
            elif isinstance(last_watered_date, (datetime, date)):
                lw_date = last_watered_date if isinstance(last_watered_date, date) else last_watered_date.date()
            else:
                lw_date = today
            days_since = max(0, (today - lw_date).days)
        except Exception:
            days_since = 1
    else:
        days_since = 1  # Default to 1 day ago if unrecorded

    # 1. Base interval
    p_type_norm = (plant_type or "").lower().strip()
    base_days = base_watering_days or PLANT_BASE_INTERVALS.get(p_type_norm, 2)
    adjusted_interval = float(base_days)

    temp = weather_data.get("temperature", 25.0)
    humidity = weather_data.get("humidity", 50.0)
    precip = weather_data.get("precipitation", 0.0)
    loc = (location_type or "Balcony").lower()

    reasons = []

    # 2. Precipitation check
    # If substantial rain recently/currently, outdoor balcony/terrace pots are saturated
    if precip >= 1.5 and loc in ["balcony", "terrace", "window box"]:
        status = "No watering needed today"
        badge_color = "green"
        rationale = f"Recent rainfall ({precip} mm) detected. Container potting mix is sufficiently saturated."
        return {
            "status": status,
            "badge_color": badge_color,
            "rationale": rationale,
            "days_since_watered": days_since,
            "adjusted_interval": adjusted_interval,
            "urgency": "low"
        }

    # 3. Temperature adjustment
    if temp >= 35.0:
        adjusted_interval -= 1.0
        reasons.append(f"Intense heat ({temp}°C) accelerates moisture loss")
    elif temp >= 30.0:
        adjusted_interval -= 0.5
        reasons.append(f"Warm weather ({temp}°C) speeds up soil drying")
    elif temp < 18.0:
        adjusted_interval += 1.0
        reasons.append(f"Cool temperatures ({temp}°C) slow evaporation")

    # 4. Humidity adjustment
    if humidity >= 75.0:
        adjusted_interval += 0.5
        reasons.append(f"High humidity ({humidity}%) retains moisture longer")
    elif humidity < 35.0:
        adjusted_interval -= 0.5
        reasons.append(f"Dry ambient air ({humidity}%) rapidly dehydrates container soil")

    # 5. Balcony / Terrace container factor
    # Potted soil on elevated floors with direct breeze dries 25-40% faster than ground beds
    if loc in ["balcony", "terrace"]:
        adjusted_interval -= 0.3
        reasons.append("Balcony/terrace wind & container exposure enhances transpiration")

    # Keep adjusted interval realistic (minimum 1 day for moisture check)
    adjusted_interval = max(1.0, round(adjusted_interval, 1))

    # 6. Recommendation logic
    # If already watered today:
    if days_since == 0:
        if temp >= 36.0 and loc in ["balcony", "terrace"] and p_type_norm in ["tomato", "mint", "basil"]:
            status = "Water today"
            badge_color = "yellow"
            rationale = "Watered earlier, but extreme heat may warrant an evening moisture check."
            urgency = "moderate"
        else:
            status = "No watering needed today"
            badge_color = "green"
            rationale = "Already watered today. Soil moisture is optimal."
            urgency = "low"
    elif days_since >= adjusted_interval:
        status = "Water today"
        badge_color = "red"
        rationale = f"Due for watering ({days_since} days since last drink). " + "; ".join(reasons)
        urgency = "high"
    elif days_since >= (adjusted_interval - 0.8):
        status = "Water tomorrow"
        badge_color = "yellow"
        rationale = f"Soil moisture is adequate today, but check tomorrow. " + "; ".join(reasons)
        urgency = "medium"
    else:
        status = "No watering needed today"
        badge_color = "green"
        rationale = f"Container soil retains ample moisture ({days_since} days since watering). " + "; ".join(reasons)
        urgency = "low"

    return {
        "status": status,
        "badge_color": badge_color,
        "rationale": rationale,
        "days_since_watered": days_since,
        "adjusted_interval": adjusted_interval,
        "urgency": urgency
    }
