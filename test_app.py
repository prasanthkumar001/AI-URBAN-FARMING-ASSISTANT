"""
Comprehensive Automated Test Suite for AI Urban Farming Assistant.
Verifies:
  - Authentication (Registration, Scrypt Hashing, Password Confirmation, Login, Logout)
  - Strict Multi-Tenant Data Isolation (User A vs User B)
  - MobileNetV2 Leaf Disease Classification & Knowledge Base
  - Low-confidence uncertainty warning threshold
  - Open-Meteo Weather integration & Smart Watering logic
  - Web Application End-to-End Routing & Protection
"""

import os
import uuid
import unittest
import json
import sqlite3
from io import BytesIO
from werkzeug.security import check_password_hash

import database as db
import ai_model
import weather_service
import business_service
import voice_assistant_service
from app import app


class TestUrbanFarmingAssistant(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        db.init_db()

    # ==================== 1. Authentication & Security Tests ====================

    def test_01_secure_password_hashing(self):
        """Verify passwords are never stored in plain text and use secure hashes."""
        uname = f"sec_user_{uuid.uuid4().hex[:6]}"
        email = f"sec_{uuid.uuid4().hex[:6]}@urban.farm"
        raw_password = "SecretPassword99!"

        user_id, err = db.register_user(uname, email, raw_password)
        self.assertIsNone(err)
        self.assertIsNotNone(user_id)
        
        with db.get_db() as conn:
            row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
            stored_hash = row["password_hash"]

        # Assert password is NOT plain text
        self.assertNotEqual(stored_hash, raw_password)
        self.assertTrue(stored_hash.startswith("scrypt:") or stored_hash.startswith("pbkdf2:"))
        self.assertTrue(check_password_hash(stored_hash, raw_password))
        self.assertFalse(check_password_hash(stored_hash, "WrongPassword"))

    def test_02_registration_validation_and_confirmation(self):
        """Test registration endpoint with valid and invalid password confirmation."""
        # Test password mismatch via web client
        res_mismatch = self.client.post("/register", data={
            "username": f"mismatch_{uuid.uuid4().hex[:6]}",
            "email": f"mismatch_{uuid.uuid4().hex[:6]}@example.com",
            "password": "Password123!",
            "confirm_password": "DifferentPassword123!"
        }, follow_redirects=True)
        self.assertIn(b"Passwords do not match", res_mismatch.data)

        # Test successful registration with matching confirmation
        test_uname = f"jenny_{uuid.uuid4().hex[:6]}"
        test_email = f"jenny_{uuid.uuid4().hex[:6]}@example.com"
        res_ok = self.client.post("/register", data={
            "username": test_uname,
            "email": test_email,
            "password": "Password123!",
            "confirm_password": "Password123!"
        }, follow_redirects=True)
        self.assertIn(b"Welcome to KrishiNova", res_ok.data)
        self.assertIn(test_uname.encode(), res_ok.data)

    def test_03_login_and_logout_flow(self):
        """Test login with good and bad credentials, and session clearing on logout."""
        # Bad login credentials
        res_fail = self.client.post("/login", data={
            "login_id": "nonexistent_grower",
            "password": "BadPassword123"
        }, follow_redirects=True)
        self.assertIn(b"Invalid username/email or password", res_fail.data)

        # Successful login
        res_login = self.client.post("/login", data={
            "login_id": "demo_farmer",
            "password": "Password123!"
        }, follow_redirects=True)
        self.assertIn(b"Welcome back", res_login.data)
        self.assertIn(b"Dashboard", res_login.data)

        # Logout
        res_logout = self.client.get("/logout", follow_redirects=True)
        self.assertIn(b"You have been safely logged out", res_logout.data)

    def test_04_unauthenticated_route_protection(self):
        """Ensure protected routes redirect unauthenticated users to /login."""
        protected_urls = ["/dashboard", "/plants", "/diagnose", "/weather", "/history"]
        for url in protected_urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 302)
            self.assertIn("/login", res.headers.get("Location", ""))

    # ==================== 2. Multi-Tenant User Data Isolation ====================

    def test_05_strict_user_data_isolation(self):
        """Verify User A cannot view, modify, or delete User B's plants or health logs."""
        # Create User A and User B
        uid_a, _ = db.register_user("tenant_alice", "alice@urban.org", "Password123!")
        if not uid_a:
            uid_a = db.authenticate_user("tenant_alice", "Password123!")[0]["id"]

        uid_b, _ = db.register_user("tenant_bob", "bob@urban.org", "Password123!")
        if not uid_b:
            uid_b = db.authenticate_user("tenant_bob", "Password123!")[0]["id"]

        # Add plant for Alice
        plant_a_id = db.add_plant(uid_a, "Alice Red Cherry", "Cherry Tomato", "2026-10-01", "Balcony")
        # Add plant for Bob
        plant_b_id = db.add_plant(uid_b, "Bob Terrace Mint", "Mint", "2026-10-01", "Terrace")

        # Query Alice's plants
        alice_plants = db.get_user_plants(uid_a)
        alice_plant_names = [p["plant_name"] for p in alice_plants]
        self.assertIn("Alice Red Cherry", alice_plant_names)
        self.assertNotIn("Bob Terrace Mint", alice_plant_names)

        # Query Bob's plants
        bob_plants = db.get_user_plants(uid_b)
        bob_plant_names = [p["plant_name"] for p in bob_plants]
        self.assertIn("Bob Terrace Mint", bob_plant_names)
        self.assertNotIn("Alice Red Cherry", bob_plant_names)

        # Cross-tenant get check
        self.assertIsNone(db.get_user_plant_by_id(uid_a, plant_b_id))
        self.assertIsNone(db.get_user_plant_by_id(uid_b, plant_a_id))

        # Alice cannot delete Bob's plant
        deleted = db.delete_user_plant(uid_a, plant_b_id)
        self.assertFalse(deleted)
        self.assertIsNotNone(db.get_user_plant_by_id(uid_b, plant_b_id))

        # Alice cannot add health log to Bob's plant
        log_id, err = db.add_health_log(uid_a, plant_b_id, "Tomato - Healthy", 90.0, "fake.jpg", "None", "None", "None")
        self.assertIsNone(log_id)
        self.assertIn("does not belong to you", err)

    # ==================== 3. MobileNetV2 Leaf Disease Detection ====================

    def test_06_mobilenet_classification_inference(self):
        """Test MobileNetV2 inference on test sample images."""
        sample_path = os.path.join(os.path.dirname(__file__), "static", "uploads", "samples", "healthy_tomato.jpg")
        self.assertTrue(os.path.exists(sample_path), "Sample test image must exist")

        res = ai_model.diagnose_leaf(sample_path)
        self.assertIn("disease_name", res)
        self.assertIn("confidence", res)
        self.assertIn("symptoms", res)
        self.assertIn("treatment", res)
        self.assertIn("prevention", res)
        self.assertIsInstance(res["confidence"], float)
        self.assertGreaterEqual(res["confidence"], 0.0)
        self.assertLessEqual(res["confidence"], 100.0)

    def test_07_low_confidence_warning_detection(self):
        """Verify that when confidence is low or image is ambiguous, warning is triggered."""
        amb_path = os.path.join(os.path.dirname(__file__), "static", "uploads", "samples", "uncertain_leaf.jpg")
        self.assertTrue(os.path.exists(amb_path), "Uncertain test image must exist")

        # Set high confidence threshold (e.g. 95%) or test with ambiguous leaf
        res = ai_model.diagnose_leaf(amb_path, confidence_threshold=90.0)
        self.assertTrue(res["is_low_confidence"])
        self.assertIsNotNone(res["warning"])
        self.assertIn("uncertainty warning", res["warning"].lower())

    # ==================== 4. Weather & Smart Watering System ====================

    def test_08_open_meteo_weather_fetch(self):
        """Verify Open-Meteo returns temperature, humidity, and precipitation."""
        weather = weather_service.fetch_current_weather("New Delhi")
        self.assertIn("temperature", weather)
        self.assertIn("humidity", weather)
        self.assertIn("precipitation", weather)
        self.assertIn("condition", weather)
        self.assertIsInstance(weather["temperature"], (int, float))

    def test_09_smart_watering_recommendation_logic(self):
        """Verify the 3 watering statuses: 'Water today', 'Water tomorrow', 'No watering needed today'."""
        from datetime import date, timedelta
        today_str = date.today().strftime("%Y-%m-%d")
        three_days_ago = (date.today() - timedelta(days=3)).strftime("%Y-%m-%d")
        two_days_ago = (date.today() - timedelta(days=2)).strftime("%Y-%m-%d")

        # Scenario 1: Plant watered today in normal conditions -> No watering needed today
        rec1 = weather_service.calculate_smart_watering(
            plant_type="Tomato",
            base_watering_days=2,
            last_watered_date=today_str,
            location_type="Balcony",
            weather_data={"temperature": 25.0, "humidity": 55.0, "precipitation": 0.0}
        )
        self.assertEqual(rec1["status"], "No watering needed today")

        # Scenario 2: Tomato not watered in 3 days in 34°C heat -> Water today
        rec2 = weather_service.calculate_smart_watering(
            plant_type="Tomato",
            base_watering_days=2,
            last_watered_date=three_days_ago,
            location_type="Balcony",
            weather_data={"temperature": 34.0, "humidity": 40.0, "precipitation": 0.0}
        )
        self.assertEqual(rec2["status"], "Water today")

        # Scenario 3: Significant rain (5mm) -> No watering needed today
        rec3 = weather_service.calculate_smart_watering(
            plant_type="Tomato",
            base_watering_days=2,
            last_watered_date=two_days_ago,
            location_type="Balcony",
            weather_data={"temperature": 24.0, "humidity": 85.0, "precipitation": 5.0}
        )
        self.assertEqual(rec3["status"], "No watering needed today")
        self.assertIn("rainfall", rec3["rationale"].lower())

    # ==================== 6. Smart Weather Monitoring & Alerts Tests ====================

    def test_11_plant_temperature_classification(self):
        """Verify plant-specific condition categories: Optimal, Minimum / Too Low, Maximum / Too High."""
        tomato = {
            "plant_name": "Test Tomato",
            "plant_type": "Tomato",
            "preferred_temp_optimal_min": 18.0,
            "preferred_temp_optimal_max": 27.0,
            "preferred_temp_min": 10.0,
            "preferred_temp_max": 35.0
        }

        # 1. Optimal conditions (23°C)
        weather_opt = {"temperature": 23.0, "forecast": [{"max_temp": 26.0, "min_temp": 19.0}]}
        res_opt = weather_service.evaluate_plant_temperature_status(tomato, weather_opt)
        self.assertEqual(res_opt["status"], "Optimal")
        self.assertIn("ideal", res_opt["detail"].lower())

        # 2. Too Low conditions (7°C)
        weather_cold = {"temperature": 7.0, "forecast": [{"max_temp": 12.0, "min_temp": 5.0}]}
        res_cold = weather_service.evaluate_plant_temperature_status(tomato, weather_cold)
        self.assertEqual(res_cold["status"], "Minimum / Too Low")
        self.assertIn("drops below", res_cold["detail"].lower())

        # 3. Too High conditions (38°C)
        weather_hot = {"temperature": 38.0, "forecast": [{"max_temp": 39.0, "min_temp": 28.0}]}
        res_hot = weather_service.evaluate_plant_temperature_status(tomato, weather_hot)
        self.assertEqual(res_hot["status"], "Maximum / Too High")
        self.assertIn("exceeds", res_hot["detail"].lower())

    def test_12_weather_alerts_engine_and_deduplication(self):
        """Verify automated alert creation, 12-hour MD5 deduplication, and resolution."""
        user_dict, _ = db.authenticate_user("demo_farmer", "Password123!")
        uid = user_dict["id"]
        dedup_key = f"test_alert_hash_{uuid.uuid4().hex[:8]}"

        # 1. Create alert
        alert_id = db.create_weather_alert(
            user_id=uid,
            severity="Critical",
            alert_type="Heatwave",
            affected_name="Greenhouse Tomato",
            explanation="Extreme heatwave risk.",
            recommended_action="Deploy shade nets and misting.",
            expected_time="Next 6 Hours",
            dedup_hash=dedup_key
        )
        self.assertIsNotNone(alert_id)

        # 2. Duplicate within 12h should be suppressed
        dup_id = db.create_weather_alert(
            user_id=uid,
            severity="Critical",
            alert_type="Heatwave",
            affected_name="Greenhouse Tomato",
            explanation="Extreme heatwave risk duplicate.",
            recommended_action="Deploy shade nets.",
            expected_time="Next 6 Hours",
            dedup_hash=dedup_key
        )
        self.assertIsNone(dup_id, "Duplicate alert with identical dedup_hash must be suppressed")

        # 3. Mark alert resolved
        res_resolve = db.mark_alert_resolved(uid, alert_id)
        self.assertTrue(res_resolve)
        active_alerts = db.get_user_weather_alerts(uid, active_only=True)
        active_ids = [a["id"] for a in active_alerts]
        self.assertNotIn(alert_id, active_ids)

    def test_13_smart_watering_4_tiers_and_overrides(self):
        """Test all 4 watering statuses and overrides (soil moisture, approaching rain, growth stage)."""
        from datetime import date, timedelta
        today_str = date.today().strftime("%Y-%m-%d")
        three_days_ago = (date.today() - timedelta(days=3)).strftime("%Y-%m-%d")

        # 1. 'Water today': Due date passed and dry
        p_due = {
            "plant_name": "Due Tomato",
            "plant_type": "Tomato",
            "base_watering_days": 2,
            "last_watered_date": three_days_ago,
            "growth_stage": "Flowering",
            "soil_moisture": "Moderate",
            "location_type": "Balcony"
        }
        res_due = weather_service.calculate_smart_watering(p_due, {"temperature": 28.0, "precipitation": 0.0, "approaching_rain_24h": 0.0})
        self.assertEqual(res_due["status"], "Water today")
        self.assertTrue(res_due["is_estimate"])

        # 2. 'Check soil before watering': Approaching heavy rain (12mm)
        p_rain_ahead = dict(p_due)
        res_rain_ahead = weather_service.calculate_smart_watering(p_rain_ahead, {"temperature": 24.0, "precipitation": 0.0, "approaching_rain_24h": 12.0})
        self.assertEqual(res_rain_ahead["status"], "Check soil before watering")

        # 3. 'No watering needed today': Soil is Wet/Saturated
        p_wet = dict(p_due)
        p_wet["soil_moisture"] = "Wet"
        res_wet = weather_service.calculate_smart_watering(p_wet, {"temperature": 25.0, "precipitation": 0.0})
        self.assertEqual(res_wet["status"], "No watering needed today")

        # 4. 'Water tomorrow': Approaching due interval tomorrow
        yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        p_tmrw = {
            "plant_name": "Pepper Pot",
            "plant_type": "Pepper",
            "base_watering_days": 2,
            "last_watered_date": yesterday_str,
            "growth_stage": "Vegetative",
            "soil_moisture": "Moderate",
            "location_type": "Balcony"
        }
        res_tmrw = weather_service.calculate_smart_watering(p_tmrw, {"temperature": 25.0, "precipitation": 0.0, "approaching_rain_24h": 0.0})
        self.assertEqual(res_tmrw["status"], "Water tomorrow")

    # ==================== 7. Business Mode & Permissions Tests ====================

    def test_14_mode_switcher_and_business_authorization(self):
        """Test mode switching between Personal Garden and Commercial Business Mode, and @business_required guard."""
        # Unauthenticated request to /business must redirect to login
        res_unauth = self.client.get("/business")
        self.assertEqual(res_unauth.status_code, 302)
        self.assertIn("/login", res_unauth.headers.get("Location", ""))

        # Login with demo farmer
        self.client.post("/login", data={
            "login_id": "demo_farmer",
            "password": "Password123!"
        })

        # Switch to business mode
        res_switch_biz = self.client.get("/switch-mode/business", follow_redirects=True)
        self.assertEqual(res_switch_biz.status_code, 200)
        self.assertIn(b"Nursery & Garden Business Mode", res_switch_biz.data)

        # Switch back to personal mode
        res_switch_pers = self.client.get("/switch-mode/personal", follow_redirects=True)
        self.assertEqual(res_switch_pers.status_code, 200)
        self.assertIn(b"My Urban Plants", res_switch_pers.data)

    def test_15_nursery_inventory_management_and_stock_adjustments(self):
        """Test adding nursery inventory, low-stock detection, stock adjustments, and sale revenue logs."""
        user_dict, _ = db.authenticate_user("demo_farmer", "Password123!")
        uid = user_dict["id"]
        biz = db.get_or_create_user_business(uid)
        biz_id = biz["id"]

        # Add inventory item
        sku_name = f"Test Cherry Tomato {uuid.uuid4().hex[:4]}"
        item_id = db.add_inventory_item(
            biz_id=biz_id,
            plant_name=sku_name,
            species="Lycopersicon esculentum",
            category="Vegetable",
            quantity=15,
            low_stock_threshold=5,
            purchase_cost=2.00,
            selling_price=5.00,
            supplier="Organic Seeds Co",
            location_zone="Greenhouse A"
        )
        self.assertIsNotNone(item_id)

        # Record Sale adjustment (sell 3 units at $5.00)
        success, err = db.adjust_inventory_stock(
            biz_id=biz_id,
            user_id=uid,
            item_id=item_id,
            movement_type="Sale",
            quantity_change=3,
            unit_price=5.00,
            notes="Customer sale"
        )
        self.assertTrue(success)
        self.assertIsNone(err)

        # Check updated stock (15 - 3 = 12)
        items = db.get_business_inventory(biz_id, search=sku_name)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["quantity"], 12)

        # Record Restock adjustment (restock 5 units)
        success_re, _ = db.adjust_inventory_stock(
            biz_id=biz_id,
            user_id=uid,
            item_id=item_id,
            movement_type="Restock",
            quantity_change=5,
            unit_price=2.00,
            notes="Vendor shipment"
        )
        self.assertTrue(success_re)
        items_re = db.get_business_inventory(biz_id, search=sku_name)
        self.assertEqual(items_re[0]["quantity"], 17)

        # Test over-sale prevention
        fail_sale, fail_err = db.adjust_inventory_stock(
            biz_id=biz_id,
            user_id=uid,
            item_id=item_id,
            movement_type="Sale",
            quantity_change=50,
            notes="Excessive sale attempt"
        )
        self.assertFalse(fail_sale)
        self.assertIn("Insufficient stock", fail_err)

    def test_16_commercial_plant_batches_and_manager_review(self):
        """Test commercial batch registration, health logging, and manager sign-off."""
        user_dict, _ = db.authenticate_user("demo_farmer", "Password123!")
        uid = user_dict["id"]
        biz = db.get_or_create_user_business(uid)
        biz_id = biz["id"]

        batch_name = f"Batch-TST-{uuid.uuid4().hex[:4]}"
        batch_id = db.add_plant_batch(
            biz_id=biz_id,
            batch_name=batch_name,
            plant_type="Tomato",
            growing_area="Polyhouse 2",
            quantity=60,
            health_status="Good"
        )
        self.assertIsNotNone(batch_id)

        # Manager review
        review_ok = db.review_plant_batch(
            biz_id=biz_id,
            batch_id=batch_id,
            health_status="Excellent",
            manager_notes="Inspected by nursery supervisor. Zero blight signs."
        )
        self.assertTrue(review_ok)

        batches = db.get_business_batches(biz_id)
        matching = [b for b in batches if b["id"] == batch_id]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["health_status"], "Excellent")
        self.assertEqual(matching[0]["manager_reviewed"], 1)

    def test_17_care_card_generation_and_view(self):
        """Test printable care card generator templates and web endpoint."""
        card_tomato = business_service.get_care_guide_for_plant("Tomato")
        self.assertIn("watering", card_tomato)
        self.assertIn("sunlight", card_tomato)
        self.assertIn("temp_range", card_tomato)
        self.assertIn("warning", card_tomato)
        self.assertIn("customer_tip", card_tomato)

        card_custom = business_service.get_care_guide_for_plant("Rare Orchid", plant_name="Dendrobium")
        self.assertIn("Dendrobium", card_custom["title"])

        # Web view test
        self.client.post("/login", data={"login_id": "demo_farmer", "password": "Password123!"})
        res = self.client.get("/business/care-cards?crop=tomato")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Customer Care Sheet Generator", res.data)
        self.assertIn(b"Print Care Sheet", res.data)

    def test_18_business_csv_report_exports(self):
        """Test downloadable CSV reports: inventory, low stock, batches, and sales."""
        self.client.post("/login", data={"login_id": "demo_farmer", "password": "Password123!"})

        # 1. Inventory CSV
        res_inv = self.client.get("/business/reports/export?type=inventory")
        self.assertEqual(res_inv.status_code, 200)
        self.assertEqual(res_inv.mimetype, "text/csv")
        self.assertIn(b"Item ID,Plant Name", res_inv.data)

        # 2. Low Stock CSV
        res_low = self.client.get("/business/reports/export?type=low_stock")
        self.assertEqual(res_low.status_code, 200)
        self.assertEqual(res_low.mimetype, "text/csv")
        self.assertIn(b"Current Stock,Threshold", res_low.data)

        # 3. Batches CSV
        res_bat = self.client.get("/business/reports/export?type=batches")
        self.assertEqual(res_bat.status_code, 200)
        self.assertEqual(res_bat.mimetype, "text/csv")
        self.assertIn(b"Batch ID,Batch Name", res_bat.data)

        # 4. Sales CSV
        res_sales = self.client.get("/business/reports/export?type=sales")
        self.assertEqual(res_sales.status_code, 200)
        self.assertEqual(res_sales.mimetype, "text/csv")
        self.assertIn(b"Transaction ID,Plant Name", res_sales.data)

    def test_19_growing_zone_weather_risk_assessment(self):
        """Test weather risk assessment across commercial growing zones (Greenhouse, Shade Net, Outdoor Benches)."""
        risks = business_service.generate_business_weather_risk_summary(biz_id=1, city="New Delhi")
        self.assertIn("weather", risks)
        self.assertIn("zones", risks)
        zone_names = [z["zone"] for z in risks["zones"]]
        self.assertTrue(any("Greenhouse" in zn for zn in zone_names))
        self.assertTrue(any("Shade Net" in zn for zn in zone_names))
    def test_20_multilingual_language_selection_and_persistence(self):
        """Test language switching endpoint (/set-language/<lang>) and registration language persistence."""
        # Test switching across all 4 languages: en, hi, gu, te
        for lang in ["gu", "hi", "te", "en"]:
            res = self.client.get(f"/set-language/{lang}", follow_redirects=True)
            self.assertEqual(res.status_code, 200)

        # Test registration with Gujarati preference
        gu_user = f"kisan_{uuid.uuid4().hex[:6]}"
        res_reg = self.client.post("/register", data={
            "username": gu_user,
            "email": f"{gu_user}@farm.in",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "role": "home_gardener",
            "preferred_language": "gu"
        }, follow_redirects=True)
        self.assertEqual(res_reg.status_code, 200)

        # Verify language persisted in database
        user_record, _ = db.authenticate_user(gu_user, "Password123!")
        self.assertIsNotNone(user_record)
        self.assertEqual(user_record.get("preferred_language"), "gu")

        # Update language in DB to Telugu
        db.update_user_language(user_record["id"], "te")
        u_updated = db.get_user_by_id(user_record["id"])
        self.assertEqual(u_updated.get("preferred_language"), "te")

    def test_21_ai_voice_doubts_clarification_multilingual(self):
        """Test KrishiNova Voice AI doubts clarification API in English, Gujarati, Hindi, and Telugu."""
        # 1. English query
        res_en = self.client.post("/api/ai-clarify-doubt", json={
            "query": "How often should I water my tomato plants in hot summer?",
            "language": "en"
        })
        self.assertEqual(res_en.status_code, 200)
        data_en = res_en.get_json()
        self.assertTrue(data_en["success"])
        self.assertEqual(data_en["speech_locale"], "en-IN")
        self.assertIn("water", data_en["speech_text"].lower())

        # 2. Gujarati query
        res_gu = self.client.post("/api/ai-clarify-doubt", json={
            "query": "ટામેટાના પાંદડા પીળા પડી જાય છે શું કરવું?",
            "language": "gu"
        })
        self.assertEqual(res_gu.status_code, 200)
        data_gu = res_gu.get_json()
        self.assertTrue(data_gu["success"])
        self.assertEqual(data_gu["speech_locale"], "gu-IN")
        self.assertIn("લીમડા", data_gu["speech_text"])

        # 3. Hindi query
        res_hi = self.client.post("/api/ai-clarify-doubt", json={
            "query": "मिर्च के पौधों में कीड़े कैसे हटाएं और नीम तेल कैसे बनाएं?",
            "language": "hi"
        })
        self.assertEqual(res_hi.status_code, 200)
        data_hi = res_hi.get_json()
        self.assertTrue(data_hi["success"])
        self.assertEqual(data_hi["speech_locale"], "hi-IN")
        self.assertIn("नीम", data_hi["speech_text"])

        # 4. Telugu query
        res_te = self.client.post("/api/ai-clarify-doubt", json={
            "query": "కుండీలలో కూరగాయలకు ఏ సేంద్రియ ఎరువు మంచిది?",
            "language": "te"
        })
        self.assertEqual(res_te.status_code, 200)
        data_te = res_te.get_json()
        self.assertTrue(data_te["success"])
        self.assertEqual(data_te["speech_locale"], "te-IN")
        self.assertIn("ఎరువు", data_te["speech_text"])


if __name__ == "__main__":
    unittest.main()

