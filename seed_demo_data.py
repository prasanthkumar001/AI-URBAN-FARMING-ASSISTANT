"""
Seed script to create sample leaf images and demo urban gardens.
Generates test images for MobileNetV2 diagnosis and seeds database tables,
including commercial nursery inventory, batches, sales, and weather alerts.
"""

import os
from PIL import Image, ImageDraw, ImageFilter
from datetime import datetime, timedelta

import database as db
import weather_service

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads", "samples")
os.makedirs(SAMPLE_DIR, exist_ok=True)


def generate_sample_images():
    """Generates synthetic test leaf images with distinct visual patterns."""
    
    # 1. Healthy Tomato Leaf (Lush vibrant green with leaf structure)
    healthy_img = Image.new("RGB", (256, 256), color=(240, 248, 240))
    draw = ImageDraw.Draw(healthy_img)
    draw.polygon([(128, 20), (220, 120), (170, 230), (128, 210), (86, 230), (36, 120)], fill=(46, 139, 87))
    draw.line([(128, 20), (128, 210)], fill=(34, 110, 65), width=3)
    for y in range(50, 190, 25):
        draw.line([(128, y), (190, y - 20)], fill=(40, 120, 70), width=2)
        draw.line([(128, y), (66, y - 20)], fill=(40, 120, 70), width=2)
    healthy_img = healthy_img.filter(ImageFilter.GaussianBlur(1))
    healthy_path = os.path.join(SAMPLE_DIR, "healthy_tomato.jpg")
    healthy_img.save(healthy_path, "JPEG", quality=95)

    # 2. Early Blight Sample (Target concentric necrotic rings)
    blight_img = Image.new("RGB", (256, 256), color=(240, 248, 240))
    draw = ImageDraw.Draw(blight_img)
    draw.polygon([(128, 20), (220, 120), (170, 230), (128, 210), (86, 230), (36, 120)], fill=(60, 130, 80))
    lesion_centers = [(100, 100), (160, 140), (110, 170)]
    for cx, cy in lesion_centers:
        draw.ellipse([cx - 28, cy - 28, cx + 28, cy + 28], fill=(160, 140, 30))
        draw.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], fill=(70, 45, 20))
        draw.ellipse([cx - 13, cy - 13, cx + 13, cy + 13], fill=(110, 70, 30))
        draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(40, 25, 10))
    blight_img = blight_img.filter(ImageFilter.GaussianBlur(1))
    blight_path = os.path.join(SAMPLE_DIR, "early_blight.jpg")
    blight_img.save(blight_path, "JPEG", quality=95)

    # 3. Bacterial Spot Sample (Numerous small dark angular specks with halos)
    bact_img = Image.new("RGB", (256, 256), color=(240, 248, 240))
    draw = ImageDraw.Draw(bact_img)
    draw.polygon([(128, 20), (220, 120), (170, 230), (128, 210), (86, 230), (36, 120)], fill=(70, 130, 70))
    import random
    random.seed(42)
    for _ in range(35):
        rx = random.randint(70, 180)
        ry = random.randint(50, 190)
        r = random.randint(3, 7)
        draw.ellipse([rx - r - 2, ry - r - 2, rx + r + 2, ry + r + 2], fill=(170, 160, 40))
        draw.ellipse([rx - r, ry - r, rx + r, ry + r], fill=(30, 25, 20))
    bact_img = bact_img.filter(ImageFilter.GaussianBlur(1))
    bact_path = os.path.join(SAMPLE_DIR, "bacterial_spot.jpg")
    bact_img.save(bact_path, "JPEG", quality=95)

    # 4. Uncertain / Ambiguous Leaf
    amb_img = Image.new("RGB", (256, 256), color=(200, 200, 195))
    draw = ImageDraw.Draw(amb_img)
    draw.polygon([(128, 30), (200, 120), (160, 210), (128, 190), (96, 210), (56, 120)], fill=(150, 160, 140))
    draw.line([(128, 30), (128, 190)], fill=(130, 140, 120), width=2)
    amb_img = amb_img.filter(ImageFilter.GaussianBlur(4))
    amb_path = os.path.join(SAMPLE_DIR, "uncertain_leaf.jpg")
    amb_img.save(amb_path, "JPEG", quality=90)

    print("Sample test leaf images generated in static/uploads/samples/")


def seed_database():
    """Seeds demo user, personal garden plants, and commercial nursery data."""
    db.init_db()

    # Create demo farmer user
    user_id, err = db.register_user("demo_farmer", "demo@urban.farm", "Password123!", role="nursery_owner")
    if err and "already exists" not in err and "already registered" not in err:
        print(f"User registration note: {err}")

    # Retrieve user ID
    user_dict, _ = db.authenticate_user("demo_farmer", "Password123!")
    if not user_dict:
        print("Failed to authenticate demo user.")
        return

    uid = user_dict["id"]
    today_str = datetime.now().strftime("%Y-%m-%d")
    two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

    # Ensure role is nursery_owner
    with db.get_db() as conn:
        conn.cursor().execute("UPDATE users SET role = 'nursery_owner' WHERE id = ?", (uid,))
        conn.commit()

    # 1. Personal Garden Plants
    existing_plants = db.get_user_plants(uid)
    if not existing_plants:
        print("Seeding initial personal plants for demo_farmer...")
        p1 = db.add_plant(
            user_id=uid,
            plant_name="Balcony Roma Tomato",
            plant_type="Tomato",
            location_type="Balcony",
            city="New Delhi",
            planting_date="2026-09-15",
            base_watering_days=2,
            growth_stage="Flowering",
            soil_moisture="Dry",
            notes="12-inch terracotta pot on south-facing balcony"
        )
        db.update_plant_watering(uid, p1, two_days_ago)

        p2 = db.add_plant(
            user_id=uid,
            plant_name="Terrace Sweet Basil",
            plant_type="Basil",
            location_type="Terrace",
            city="New Delhi",
            planting_date="2026-09-22",
            base_watering_days=1,
            growth_stage="Vegetative",
            soil_moisture="Dry",
            notes="Herb planter box with vermicompost"
        )
        db.update_plant_watering(uid, p2, two_days_ago)

        p3 = db.add_plant(
            user_id=uid,
            plant_name="Balcony Bell Pepper",
            plant_type="Bell Pepper",
            location_type="Balcony",
            city="New Delhi",
            planting_date="2026-09-01",
            base_watering_days=3,
            growth_stage="Fruiting",
            soil_moisture="Moist",
            notes="10-inch plastic container"
        )
        db.update_plant_watering(uid, p3, today_str)

        p4 = db.add_plant(
            user_id=uid,
            plant_name="Living Room Aloe Vera",
            plant_type="Succulent",
            location_type="Indoor",
            city="New Delhi",
            planting_date="2026-08-10",
            base_watering_days=7,
            growth_stage="Vegetative",
            soil_moisture="Moderate",
            notes="Ceramic planter on sunny windowsill"
        )
        db.update_plant_watering(uid, p4, three_days_ago)

        # Initial Health Log
        db.add_health_log(
            user_id=uid,
            plant_id=p1,
            disease="Tomato - Healthy Foliage",
            confidence=89.5,
            image_path="uploads/samples/healthy_tomato.jpg",
            symptoms="Vibrant green foliage with crisp margins, sturdy stems, and no discolored spots or pest damage.",
            treatment="No treatment required. Your plant is thriving! Continue your regular balanced organic feeding and watering schedule.",
            prevention="Maintain smart watering based on real-time weather. Inspect leaf undersides once a week. Ensure 6-8 hours of sunlight.",
            notes="Routine weekly checkup"
        )
        print("Personal garden plants seeded.")
    else:
        print("Personal plants already exist.")

    # 2. Commercial Nursery Business
    biz = db.get_or_create_user_business(uid, default_name="GreenSprout Urban Nursery & Garden Centre")
    biz_id = biz["id"]
    print(f"Commercial business initialized: {biz['name']} (ID: {biz_id})")

    # 3. Commercial Nursery Inventory Items
    existing_inv = db.get_business_inventory(biz_id)
    if not existing_inv:
        print("Seeding commercial nursery inventory items...")
        item1_id = db.add_inventory_item(
            biz_id=biz_id,
            plant_name="Roma Tomato Starter Pots",
            species="Solanum lycopersicum 'Roma'",
            category="Vegetable",
            quantity=35,
            low_stock_threshold=10,
            purchase_cost=2.50,
            selling_price=6.50,
            supplier="AgriSeed Co",
            location_zone="Greenhouse A",
            health_status="Healthy",
            notes="4-inch biodegradable starter pots"
        )

        item2_id = db.add_inventory_item(
            biz_id=biz_id,
            plant_name="Sweet Basil Seedling Trays",
            species="Ocimum basilicum",
            category="Herb",
            quantity=4,  # Below threshold 8 -> Low stock trigger!
            low_stock_threshold=8,
            purchase_cost=1.20,
            selling_price=3.50,
            supplier="HerbSprout Labs",
            location_zone="Shade Net Nursery",
            health_status="Healthy",
            notes="6-pack herb cell trays; reorder imminent"
        )

        item3_id = db.add_inventory_item(
            biz_id=biz_id,
            plant_name="Bell Pepper Bush Pots",
            species="Capsicum annuum",
            category="Vegetable",
            quantity=22,
            low_stock_threshold=6,
            purchase_cost=3.00,
            selling_price=7.50,
            supplier="AgriSeed Co",
            location_zone="Greenhouse A",
            health_status="Healthy",
            notes="Well-rooted container peppers"
        )

        item4_id = db.add_inventory_item(
            biz_id=biz_id,
            plant_name="Peppermint Window Planters",
            species="Mentha piperita",
            category="Herb",
            quantity=18,
            low_stock_threshold=5,
            purchase_cost=1.80,
            selling_price=4.50,
            supplier="Local Propagation",
            location_zone="Outdoor Retail Benches",
            health_status="Healthy",
            notes="Fragrant culinary mint pots"
        )

        item5_id = db.add_inventory_item(
            biz_id=biz_id,
            plant_name="Sansevieria Snake Plant 6-in",
            species="Sansevieria trifasciata",
            category="Succulent",
            quantity=3,  # Below threshold 5 -> Low stock trigger!
            low_stock_threshold=5,
            purchase_cost=5.00,
            selling_price=14.00,
            supplier="ExoticGreen Imports",
            location_zone="Indoor Retail Showroom",
            health_status="Healthy",
            notes="Low-light architectural houseplant"
        )

        # 4. Record Real Sample Sales Transactions
        print("Recording initial sales transactions...")
        db.adjust_inventory_stock(
            biz_id=biz_id,
            user_id=uid,
            item_id=item1_id,
            movement_type="Sale",
            quantity_change=5,
            unit_price=6.50,
            notes="Weekend farmers market customer sale"
        )
        db.adjust_inventory_stock(
            biz_id=biz_id,
            user_id=uid,
            item_id=item4_id,
            movement_type="Sale",
            quantity_change=4,
            unit_price=4.50,
            notes="Walk-in retail patio customer"
        )
        print("Commercial inventory and sales records seeded.")
    else:
        print("Commercial inventory items already exist.")

    # 5. Commercial Plant Batches
    existing_batches = db.get_business_batches(biz_id)
    if not existing_batches:
        print("Seeding commercial propagation batches...")
        b1 = db.add_plant_batch(
            biz_id=biz_id,
            batch_name="Batch-TOM-2026-A",
            plant_type="Tomato",
            growing_area="Greenhouse A",
            quantity=50,
            health_status="Good"
        )
        db.review_plant_batch(
            biz_id=biz_id,
            batch_id=b1,
            health_status="Good",
            manager_notes="Vigorous seedling establishment; no damping-off detected."
        )

        b2 = db.add_plant_batch(
            biz_id=biz_id,
            batch_name="Batch-BAS-2026-B",
            plant_type="Basil",
            growing_area="Shade Net Nursery",
            quantity=30,
            health_status="Good"
        )
        db.review_plant_batch(
            biz_id=biz_id,
            batch_id=b2,
            health_status="Good",
            manager_notes="Uniform germination; true leaves forming nicely."
        )

        b3 = db.add_plant_batch(
            biz_id=biz_id,
            batch_name="Batch-PEP-2026-C",
            plant_type="Bell Pepper",
            growing_area="Greenhouse A",
            quantity=40,
            health_status="Needs Attention"
        )
        print("Commercial plant batches seeded.")
    else:
        print("Plant batches already exist.")

    # 6. Seed Sample Weather Alerts
    existing_alerts = db.get_user_weather_alerts(uid)
    if not existing_alerts:
        print("Seeding initial weather alerts...")
        db.create_weather_alert(
            user_id=uid,
            severity="Warning",
            alert_type="Temperature",
            affected_name="Balcony Roma Tomato",
            explanation="Forecast high temperature exceeds optimal growing range of 18°C – 27°C.",
            recommended_action="Ensure afternoon shade cloth is drawn and soil is kept hydrated.",
            expected_time="Upcoming 24–48 Hours",
            weather_value="33.5°C",
            preferred_range="18.0°C – 27.0°C"
        )
        db.create_weather_alert(
            user_id=uid,
            severity="Informational",
            alert_type="Smart Irrigation",
            affected_name="Living Room Aloe Vera",
            explanation="Succulent potting mix is moderately dry. Scheduled soak recommended soon.",
            recommended_action="Water thoroughly then allow complete drainage before replacing on saucer.",
            expected_time="Today",
            weather_value="Indoor 22°C",
            preferred_range="Dry to Moderate"
        )
        print("Weather alerts seeded.")
    else:
        print("Weather alerts already exist.")

    print("\nDatabase seeding completed successfully for KrishiNova!")


if __name__ == "__main__":
    generate_sample_images()
    seed_database()
