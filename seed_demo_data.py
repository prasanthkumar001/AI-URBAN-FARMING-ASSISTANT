"""
Seed script to create sample leaf images and demo urban gardens.
Generates test images for MobileNetV2 diagnosis and seeds database tables.
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
    # Leaf blade ellipse
    draw.polygon([(128, 20), (220, 120), (170, 230), (128, 210), (86, 230), (36, 120)], fill=(46, 139, 87))
    # Midrib and veins
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
    # Concentric target lesions
    lesion_centers = [(100, 100), (160, 140), (110, 170)]
    for cx, cy in lesion_centers:
        draw.ellipse([cx - 28, cy - 28, cx + 28, cy + 28], fill=(160, 140, 30))  # chlorotic yellow halo
        draw.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], fill=(70, 45, 20))    # brown outer ring
        draw.ellipse([cx - 13, cy - 13, cx + 13, cy + 13], fill=(110, 70, 30))   # inner ring
        draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(40, 25, 10))        # necrotic center
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
        draw.ellipse([rx - r - 2, ry - r - 2, rx + r + 2, ry + r + 2], fill=(170, 160, 40)) # halo
        draw.ellipse([rx - r, ry - r, rx + r, ry + r], fill=(30, 25, 20)) # black speck
    bact_img = bact_img.filter(ImageFilter.GaussianBlur(1))
    bact_path = os.path.join(SAMPLE_DIR, "bacterial_spot.jpg")
    bact_img.save(bact_path, "JPEG", quality=95)

    # 4. Uncertain / Ambiguous Leaf (Faded, washed out image to test low confidence warning)
    amb_img = Image.new("RGB", (256, 256), color=(200, 200, 195))
    draw = ImageDraw.Draw(amb_img)
    draw.polygon([(128, 30), (200, 120), (160, 210), (128, 190), (96, 210), (56, 120)], fill=(150, 160, 140))
    draw.line([(128, 30), (128, 190)], fill=(130, 140, 120), width=2)
    amb_img = amb_img.filter(ImageFilter.GaussianBlur(4)) # high blur/noise
    amb_path = os.path.join(SAMPLE_DIR, "uncertain_leaf.jpg")
    amb_img.save(amb_path, "JPEG", quality=90)

    print("Sample test leaf images generated in static/uploads/samples/")


def seed_database():
    """Seeds demo user and plants into SQLite database."""
    db.init_db()

    # Create demo farmer user
    user_id, err = db.register_user("demo_farmer", "demo@urban.farm", "Password123!")
    if err and "already exists" not in err and "already registered" not in err:
        print(f"User registration note: {err}")

    # Retrieve user ID
    user_dict, _ = db.authenticate_user("demo_farmer", "Password123!")
    if not user_dict:
        print("Failed to authenticate demo user.")
        return

    uid = user_dict["id"]
    existing_plants = db.get_user_plants(uid)

    if not existing_plants:
        print("Seeding initial plants for demo_farmer...")
        today_str = datetime.now().strftime("%Y-%m-%d")
        two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

        p1 = db.add_plant(
            user_id=uid,
            plant_name="Balcony Roma Tomato",
            plant_type="Tomato",
            location_type="Balcony",
            city="New Delhi",
            planting_date="2026-09-15",
            base_watering_days=2,
            notes="12-inch terracotta pot on south-facing balcony"
        )
        # Update last watered to 2 days ago so it prompts watering today
        db.update_plant_watering(uid, p1, two_days_ago)

        p2 = db.add_plant(
            user_id=uid,
            plant_name="Terrace Sweet Basil",
            plant_type="Basil",
            location_type="Terrace",
            city="New Delhi",
            planting_date="2026-09-22",
            base_watering_days=1,
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
            notes="Ceramic planter on sunny windowsill"
        )
        db.update_plant_watering(uid, p4, three_days_ago)

        # Add initial health diagnosis for Roma Tomato
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
        print("Demo plants and initial diagnosis seeded successfully!")
    else:
        print("Demo plants already exist in database.")


if __name__ == "__main__":
    generate_sample_images()
    seed_database()
