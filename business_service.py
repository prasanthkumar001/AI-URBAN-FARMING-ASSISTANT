"""
Nursery & Garden Business Service.
Provides inventory valuation, stock adjustments, batch health management,
care card generator, and business CSV reporting.
"""

import csv
import io
from datetime import datetime
import database as db
import weather_service

# Predefined Care Guidelines for Nursery Customer Handouts
CARE_GUIDE_TEMPLATES = {
    "tomato": {
        "title": "Tomato (Solanum lycopersicum) Nursery Care Guide",
        "watering": "Every 2 days (keep soil consistently moist, avoid wetting leaves)",
        "sunlight": "Full Sun (6 to 8 hours direct sunlight daily)",
        "temp_range": "Ideal: 18°C – 27°C (Tolerance: 10°C – 35°C)",
        "soil": "Rich, well-draining potting compost with vermicompost & perlite",
        "fertilizer": "Balanced NPK early on, transition to high-potassium formula at flowering",
        "pruning": "Pinch off side-shoot suckers for indeterminate varieties",
        "common_diseases": "Early Blight, Late Blight, Bacterial Spot, Blossom End Rot",
        "warning": "Avoid overhead sprinkler watering to prevent foliar fungal spore germination.",
        "customer_tip": "If growing on an urban balcony, rotate container 90 degrees weekly for even foliage sun exposure."
    },
    "bell pepper": {
        "title": "Bell Pepper & Capsicum Container Guide",
        "watering": "Every 2 to 3 days (allow top 2cm soil to dry between waterings)",
        "sunlight": "Full Sun (6+ hours daily)",
        "temp_range": "Ideal: 20°C – 30°C (Sensitive below 15°C)",
        "soil": "Fertile, loamy, well-drained potting mix (pH 6.0 – 6.8)",
        "fertilizer": "Feed with organic liquid seaweed/fish emulsion every 14 days",
        "pruning": "Top seedlings at 15cm height to encourage bushier branching",
        "common_diseases": "Anthracnose, Aphids, Bacterial Leaf Spot",
        "warning": "Shield from cold winds on elevated balconies or high terraces.",
        "customer_tip": "Add crushed eggshells to potting mix to provide calcium against blossom-end rot."
    },
    "chilli": {
        "title": "Chilli & Hot Pepper Growing Guide",
        "watering": "Every 3 days (drought-tolerant; overwatering reduces pepper pungency)",
        "sunlight": "Full Sun (6 to 8 hours daily)",
        "temp_range": "Ideal: 20°C – 32°C (Tolerance: 15°C – 36°C)",
        "soil": "Well-drained sandy loam or coco-peat mix with pumice",
        "fertilizer": "Moderate feeding; avoid excess nitrogen to prevent leafy foliage without fruit",
        "pruning": "Stake plants when laden with chillies to prevent stem snapping",
        "common_diseases": "Leaf Curl Virus, Spider Mites, Thrips",
        "warning": "Watch for curling leaf tips indicating thrips or mite activity.",
        "customer_tip": "Warm, sunny balconies produce the spiciest and highest-yielding chillies!"
    },
    "basil": {
        "title": "Sweet Basil Herb Pot Care Sheet",
        "watering": "Daily or every other day (bottom-water preferred; soil should stay evenly damp)",
        "sunlight": "Morning Sun or Bright Partial Light (4 to 6 hours)",
        "temp_range": "Ideal: 18°C – 30°C (Extremely frost-tender, min 12°C)",
        "soil": "Moist, nutrient-rich potting soil with good drainage",
        "fertilizer": "Light organic kelp feed once a month",
        "pruning": "Continuously pinch terminal flower buds to preserve aromatic leaf flavor",
        "common_diseases": "Fusarium Wilt, Downy Mildew",
        "warning": "Never allow potted basil to sit in cold soggy standing water.",
        "customer_tip": "Harvest top pairs of leaves in early morning for peak essential oil fragrance."
    },
    "mint": {
        "title": "Mint (Pudina) Planter Care Sheet",
        "watering": "Daily or every 2 days (loves consistent moisture; never let dry out fully)",
        "sunlight": "Partial Sun to Filtered Shade (3 to 5 hours)",
        "temp_range": "Ideal: 15°C – 25°C (Very hardy, down to 5°C)",
        "soil": "Humus-rich, moisture-retentive potting compost",
        "fertilizer": "Top-dress with vermicompost every 30 days",
        "pruning": "Cut stems back by half every two months to stimulate tender new runners",
        "common_diseases": "Mint Rust, Powdery Mildew",
        "warning": "Always grow mint in dedicated pots; invasive roots quickly choke other companion crops.",
        "customer_tip": "Thrives on north- or east-facing windowsills and balconies with partial light."
    },
    "succulent": {
        "title": "Succulent & Cactus Collection Care Guide",
        "watering": "Every 7 to 10 days (Soak-and-Dry method: soak thoroughly, dry out completely)",
        "sunlight": "Bright Indirect to Direct Morning Sun",
        "temp_range": "Ideal: 18°C – 32°C (Keep dry in cold seasons)",
        "soil": "Gritty, mineral-heavy cactus succulent mix (perlite, coarse sand, gravel)",
        "fertilizer": "Dilute cactus fertilizer once during active spring growing season",
        "pruning": "Remove shriveled lower leaves cleanly with tweezers",
        "common_diseases": "Root Rot (overwatering), Mealybugs",
        "warning": "Damp potting soil for >48 hours leads directly to basal stem and root rot.",
        "customer_tip": "If leaf petals look wrinkly, it wants a drink; if translucent or mushy, stop watering!"
    }
}


def get_care_guide_for_plant(plant_type, plant_name=None):
    """Generates customer-friendly care card dictionary."""
    key = (plant_type or "").lower().strip()
    template = None
    for k in CARE_GUIDE_TEMPLATES:
        if k in key:
            template = dict(CARE_GUIDE_TEMPLATES[k])
            break

    if not template:
        pref = db.get_plant_preference(plant_type)
        template = {
            "title": f"{plant_name or plant_type} Urban Care Sheet",
            "watering": f"Every {pref['base_watering_days']} days (check soil moisture before watering)",
            "sunlight": pref["sunlight_need"],
            "temp_range": f"Ideal: {pref['optimal_temp_min']}°C – {pref['optimal_temp_max']}°C (Limits: {pref['absolute_temp_min']}°C – {pref['absolute_temp_max']}°C)",
            "soil": "Well-draining urban container compost enriched with organic vermicompost",
            "fertilizer": "Balanced organic foliar feed every 14–21 days during active growth",
            "pruning": "Trim dead leaves and spent blooms regularly",
            "common_diseases": pref["common_diseases"],
            "warning": "Ensure drainage holes in pots are clear to prevent waterlogging.",
            "customer_tip": pref["care_tips"]
        }

    if plant_name:
        template["plant_name"] = plant_name
    template["generated_date"] = datetime.now().strftime("%B %d, %Y")
    return template


def generate_business_weather_risk_summary(biz_id, city="New Delhi"):
    """
    Evaluates weather risks across nursery growing zones (Greenhouses, Shade Nets, Outdoor Benches).
    """
    weather = weather_service.fetch_current_weather(city)
    temp = weather.get("temperature", 25.0)
    humidity = weather.get("humidity", 50.0)
    precip = weather.get("precipitation", 0.0)
    wind = weather.get("wind_speed_10m", 5.0)
    forecast = weather.get("forecast", [])
    max_temp = forecast[0]["max_temp"] if forecast else temp + 3
    min_temp = forecast[0]["min_temp"] if forecast else temp - 4

    zones_risks = [
        {
            "zone": "Greenhouse A & Polyhouse",
            "environment": "Enclosed plastic/glass",
            "risk_level": "High" if max_temp >= 32.0 else "Low",
            "status_color": "red" if max_temp >= 32.0 else "green",
            "threat": f"Extreme heat buildup ({max_temp}°C exterior can reach {max_temp+6}°C inside)" if max_temp >= 32.0 else "Optimal climate conditions",
            "action": "Open ridge vents, activate exhaust fans, run evaporative pad cooling" if max_temp >= 32.0 else "Maintain standard ventilation schedule"
        },
        {
            "zone": "Shade Net Nursery Area (50% Shade)",
            "environment": "Semi-outdoor shaded beds",
            "risk_level": "Warning" if (humidity >= 80.0 or wind >= 25.0) else "Low",
            "status_color": "amber" if (humidity >= 80.0 or wind >= 25.0) else "green",
            "threat": "High humidity fungal disease vector" if humidity >= 80.0 else ("Gusty winds flapping shade cloth" if wind >= 25.0 else "Favorable nursery growth"),
            "action": "Space seedling trays 10cm apart; inspect lower foliage for blight" if humidity >= 80.0 else "Secure shade net anchor ties"
        },
        {
            "zone": "Outdoor Retail Display Benches",
            "environment": "Direct sun & open air",
            "risk_level": "Critical" if (precip >= 15.0 or wind >= 28.0 or temp >= 35.0) else "Low",
            "status_color": "red" if (precip >= 15.0 or wind >= 28.0 or temp >= 35.0) else "green",
            "threat": "Deluge waterlogging & container toppling" if (precip >= 15.0 or wind >= 28.0) else ("Rapid pot desiccation" if temp >= 35.0 else "Pleasant shopping weather"),
            "action": "Move delicate ornamental stock under covered canopy" if (precip >= 15.0 or wind >= 28.0) else "Schedule afternoon moisture check on 4-inch pots"
        }
    ]

    return {
        "weather": weather,
        "zones": zones_risks
    }


# ==================== CSV Report Exporters ====================

def export_inventory_csv(biz_id):
    """Exports nursery inventory list to CSV string."""
    items = db.get_business_inventory(biz_id)
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        "Item ID", "Plant Name", "Species / Variety", "Category",
        "Stock Quantity", "Low Stock Threshold", "Purchase Cost ($)",
        "Selling Price ($)", "Estimated Gross Margin (%)", "Total Cost Value ($)",
        "Total Retail Value ($)", "Location Zone", "Health Status", "Supplier", "Notes"
    ])

    for it in items:
        qty = it["quantity"]
        cost = it["purchase_cost"]
        price = it["selling_price"]
        margin = round(((price - cost) / price * 100.0), 1) if price > 0 else 0.0
        total_cost = round(qty * cost, 2)
        total_retail = round(qty * price, 2)

        writer.writerow([
            it["id"], it["plant_name"], it["species"], it["category"],
            qty, it["low_stock_threshold"], f"{cost:.2f}",
            f"{price:.2f}", f"{margin}%", f"{total_cost:.2f}",
            f"{total_retail:.2f}", it["location_zone"], it["health_status"],
            it["supplier"], it["notes"]
        ])

    return output.getvalue()


def export_low_stock_csv(biz_id):
    """Exports low-stock alerts report to CSV string."""
    items = db.get_business_inventory(biz_id, low_stock_only=True)
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Item ID", "Plant Name", "Species", "Current Stock",
        "Threshold", "Units Needed to Reorder", "Supplier", "Cost Per Unit ($)"
    ])

    for it in items:
        units_needed = max(10, (it["low_stock_threshold"] * 2) - it["quantity"])
        writer.writerow([
            it["id"], it["plant_name"], it["species"], it["quantity"],
            it["low_stock_threshold"], units_needed, it["supplier"], f"{it['purchase_cost']:.2f}"
        ])

    return output.getvalue()


def export_batch_health_csv(biz_id):
    """Exports commercial batch health report to CSV."""
    batches = db.get_business_batches(biz_id)
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Batch ID", "Batch Name", "Crop Type", "Growing Area",
        "Quantity", "Health Status", "Manager Reviewed", "Review Notes", "Date Created"
    ])

    for b in batches:
        writer.writerow([
            b["id"], b["batch_name"], b["plant_type"], b["growing_area"],
            b["quantity"], b["health_status"],
            "Yes" if b["manager_reviewed"] else "Pending",
            b["review_notes"], b["created_at"]
        ])

    return output.getvalue()


def export_sales_csv(biz_id):
    """Exports recorded sales records to CSV."""
    sales = db.get_business_sales_history(biz_id, limit=500)
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Transaction ID", "Plant Name", "Species", "Quantity Sold",
        "Unit Price ($)", "Total Amount ($)", "Estimated COGS ($)",
        "Estimated Profit ($)", "Recorded By", "Date", "Notes"
    ])

    for s in sales:
        total = s["total_amount"]
        cogs = s["estimated_cogs"]
        profit = round(total - cogs, 2)
        writer.writerow([
            s["id"], s.get("plant_name") or "Item", s.get("species") or "",
            s["quantity"], f"{s['unit_price']:.2f}", f"{total:.2f}",
            f"{cogs:.2f}", f"{profit:.2f}", s.get("recorded_by", "Staff"),
            s["sale_date"], s.get("notes", "")
        ])

    return output.getvalue()
