"""
KrishiNova - Urban Farming & Garden Business Platform.
Main Flask Application providing user authentication, personal garden management,
MobileNetV2 leaf disease classification, Open-Meteo smart weather alerts,
4-tier smart watering recommendations, Commercial Nursery Business Mode,
and Multilingual Voice AI Assistant (English, Gujarati, Hindi, Telugu).
"""

import os
import uuid
from functools import wraps
from datetime import datetime, date
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, send_from_directory, Response, g
)
from werkzeug.utils import secure_filename

import database as db
import ai_model
import weather_service
import business_service
import voice_assistant_service

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "urban-farming-secret-key-2026-secure-salt-9812")

# Uploads directory
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max image size

# Initialize database tables and run non-destructive schema migrations
db.init_db()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(f):
    """Decorator to protect routes from unauthenticated access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access your personal urban farming dashboard.", "warning")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def business_required(f):
    """Decorator to enforce business membership and server-side authorization."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access the Business Dashboard.", "warning")
            return redirect(url_for("login", next=request.path))
        
        user_id = session["user_id"]
        biz = db.get_or_create_user_business(user_id)
        if not biz or not db.user_has_business_access(user_id, biz["id"]):
            flash("Unauthorized access: Business membership required.", "error")
            return redirect(url_for("dashboard"))
        
        g.business = biz
        return f(*args, **kwargs)
    return decorated_function


@app.context_processor
def inject_global_context():
    """Inject logged-in user, active mode, unread alert count, and language preferences into templates."""
    user = None
    unread_alerts = 0
    active_mode = session.get("active_mode", "personal")
    curr_lang = session.get("preferred_language", "en")
    
    if "user_id" in session:
        user_id = session["user_id"]
        u_record = db.get_user_by_id(user_id)
        if u_record:
            user_lang = u_record.get("preferred_language") or "en"
            curr_lang = session.get("preferred_language") or user_lang
            user = {
                "id": u_record["id"],
                "username": u_record["username"],
                "email": u_record["email"],
                "role": u_record.get("role", "home_gardener"),
                "preferred_language": curr_lang
            }
        else:
            user = {
                "id": user_id,
                "username": session.get("username", "Farmer"),
                "email": session.get("email", ""),
                "role": "home_gardener",
                "preferred_language": curr_lang
            }
        unread_alerts = db.get_unread_alert_count(user_id)

    # Ensure valid language
    if curr_lang not in voice_assistant_service.SUPPORTED_LANGUAGES:
        curr_lang = "en"

    return dict(
        current_user=user,
        active_mode=active_mode,
        unread_alert_count=unread_alerts,
        current_year=datetime.now().year,
        current_language=curr_lang,
        supported_languages=voice_assistant_service.SUPPORTED_LANGUAGES,
        lang_meta=voice_assistant_service.get_language_metadata(curr_lang)
    )


# ==================== Language Preference & Voice AI Routes ====================

@app.route("/set-language/<lang>")
def set_language(lang):
    """Switches preferred language (en, gu, hi, te) across session and database."""
    lang_code = (lang or "en").lower().strip()
    if lang_code in voice_assistant_service.SUPPORTED_LANGUAGES:
        session["preferred_language"] = lang_code
        if "user_id" in session:
            db.update_user_language(session["user_id"], lang_code)
    return redirect(request.referrer or url_for("dashboard" if "user_id" in session else "login"))


@app.route("/api/ai-clarify-doubt", methods=["POST"])
def api_clarify_doubt():
    """API endpoint to clarify user's voiced or typed gardening doubt in chosen language."""
    data = request.get_json(silent=True) or request.form
    query = (data.get("query") or "").strip()
    lang = data.get("language") or session.get("preferred_language", "en")
    
    if not query:
        return jsonify({"success": False, "error": "Query cannot be empty"}), 400

    result = voice_assistant_service.clarify_doubt(query, language=lang)
    return jsonify(result)


# ==================== Mode Switcher ====================

@app.route("/switch-mode/<mode>")
@login_required
def switch_mode(mode):
    """Switches navigation between Personal Garden and Business Mode."""
    if mode in ["personal", "business"]:
        session["active_mode"] = mode
        if mode == "business":
            flash("Switched to Nursery & Garden Business Mode.", "info")
            return redirect(url_for("business_dashboard"))
        else:
            flash("Switched to Personal Garden Mode.", "info")
            return redirect(url_for("dashboard"))
    return redirect(url_for("dashboard"))


# ==================== Authentication Routes ====================

@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        role = request.form.get("role", "home_gardener").strip()
        preferred_language = request.form.get("preferred_language", session.get("preferred_language", "en")).strip()

        # Password confirmation validation
        if password != confirm_password:
            flash("Passwords do not match. Please re-enter both passwords.", "error")
            return render_template("auth/register.html", username=username, email=email)

        # Register in database with secure scrypt hashing and preferred language
        user_id, error = db.register_user(username, email, password, role=role, preferred_language=preferred_language)
        if error:
            flash(error, "error")
            return render_template("auth/register.html", username=username, email=email)

        # Successful registration - auto-login
        session["user_id"] = user_id
        session["username"] = username
        session["email"] = email
        session["preferred_language"] = preferred_language
        session["active_mode"] = "business" if role in ["nursery_owner", "nursery_staff"] else "personal"
        flash(f"Welcome to KrishiNova, {username}! Your account has been created successfully.", "success")
        
        if role in ["nursery_owner", "nursery_staff"]:
            return redirect(url_for("business_dashboard"))
        return redirect(url_for("dashboard"))

    return render_template("auth/register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    next_page = request.args.get("next")

    if request.method == "POST":
        login_id = request.form.get("login_id", "").strip()
        password = request.form.get("password", "")
        next_target = request.form.get("next") or url_for("dashboard")

        user, error = db.authenticate_user(login_id, password)
        if error or not user:
            flash(error or "Invalid username/email or password.", "error")
            return render_template("auth/login.html", login_id=login_id, next=next_page)

        # Establish session
        pref_lang = user.get("preferred_language") or session.get("preferred_language", "en")
        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["email"] = user["email"]
        session["preferred_language"] = pref_lang
        session["active_mode"] = "business" if user.get("role") in ["nursery_owner", "nursery_staff"] else "personal"
        flash(f"Welcome back, {user['username']}!", "success")
        return redirect(next_target)

    return render_template("auth/login.html", next=next_page)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been safely logged out.", "info")
    return redirect(url_for("login"))


# ==================== Core Personal Garden Routes ====================

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    plants = db.get_user_plants(user_id)
    recent_logs = db.get_user_health_logs(user_id)[:5]

    # Fetch weather for primary city
    primary_city = plants[0]["city"] if plants and plants[0].get("city") else "New Delhi"
    weather = weather_service.fetch_current_weather(primary_city)

    # Automatically generate weather alerts from real forecast data
    if plants and weather.get("status") == "live":
        weather_service.generate_weather_alerts(user_id, plants, weather)

    # Fetch active alerts for alert centre display
    active_alerts = db.get_user_weather_alerts(user_id, active_only=True, limit=6)

    # Compute smart watering & temperature status for each plant
    plants_enriched = []
    urgent_water_count = 0
    temp_threat_count = 0

    for plant in plants:
        p_data = dict(plant)
        p_city = p_data.get("city", primary_city)
        p_weather = weather if p_city.lower() == primary_city.lower() else weather_service.fetch_current_weather(p_city)

        # 1. 4-Tier Smart Watering Recommendation
        watering_rec = weather_service.calculate_smart_watering(p_data, p_weather)
        p_data["watering_rec"] = watering_rec
        if watering_rec["status"] == "Water today":
            urgent_water_count += 1

        # 2. Plant-Specific Temperature Classification
        temp_status = weather_service.evaluate_plant_temperature_status(p_data, p_weather)
        p_data["temp_status"] = temp_status
        if temp_status["status"] != "Optimal":
            temp_threat_count += 1

        plants_enriched.append(p_data)

    return render_template(
        "dashboard.html",
        plants=plants_enriched,
        recent_logs=recent_logs,
        weather=weather,
        active_alerts=active_alerts,
        total_plants=len(plants),
        urgent_water_count=urgent_water_count,
        temp_threat_count=temp_threat_count
    )


# ==================== Weather Alert Centre Routes ====================

@app.route("/alerts")
@login_required
def alerts_center():
    user_id = session["user_id"]
    severity_filter = request.args.get("severity")
    show_resolved = request.args.get("show_resolved") == "true"

    all_alerts = db.get_user_weather_alerts(user_id, active_only=not show_resolved, limit=100)
    
    if severity_filter and severity_filter != "All":
        all_alerts = [a for a in all_alerts if a["severity"].lower() == severity_filter.lower()]

    return render_template(
        "alerts.html",
        alerts=all_alerts,
        severity_filter=severity_filter or "All",
        show_resolved=show_resolved
    )


@app.route("/alerts/<int:alert_id>/read", methods=["POST"])
@login_required
def alert_mark_read(alert_id):
    user_id = session["user_id"]
    db.mark_alert_read(user_id, alert_id)
    return redirect(request.referrer or url_for("alerts_center"))


@app.route("/alerts/<int:alert_id>/resolve", methods=["POST"])
@login_required
def alert_mark_resolved(alert_id):
    user_id = session["user_id"]
    db.mark_alert_resolved(user_id, alert_id)
    flash("Alert marked as resolved.", "info")
    return redirect(request.referrer or url_for("alerts_center"))


@app.route("/alerts/read-all", methods=["POST"])
@login_required
def alert_mark_all_read():
    user_id = session["user_id"]
    db.mark_all_alerts_read(user_id)
    flash("All alerts marked as read.", "info")
    return redirect(request.referrer or url_for("alerts_center"))


# ==================== Plant Management & Custom Preferences ====================

@app.route("/plants", methods=["GET", "POST"])
@login_required
def plants_view():
    user_id = session["user_id"]

    if request.method == "POST":
        plant_name = request.form.get("plant_name", "").strip()
        plant_type = request.form.get("plant_type", "Tomato").strip()
        location_type = request.form.get("location_type", "Balcony").strip()
        city = request.form.get("city", "New Delhi").strip()
        planting_date = request.form.get("planting_date", datetime.now().strftime("%Y-%m-%d")).strip()
        base_watering_days = int(request.form.get("base_watering_days", 2))
        growth_stage = request.form.get("growth_stage", "Vegetative").strip()
        soil_moisture = request.form.get("soil_moisture", "Moderate").strip()
        notes = request.form.get("notes", "").strip()

        # Custom temperature preference overrides (if provided)
        opt_min = request.form.get("opt_min")
        opt_max = request.form.get("opt_max")
        abs_min = request.form.get("abs_min")
        abs_max = request.form.get("abs_max")

        if not plant_name:
            flash("Please enter a name for your plant.", "error")
        else:
            db.add_plant(
                user_id=user_id,
                plant_name=plant_name,
                plant_type=plant_type,
                planting_date=planting_date,
                location_type=location_type,
                city=city,
                base_watering_days=base_watering_days,
                growth_stage=growth_stage,
                soil_moisture=soil_moisture,
                notes=notes,
                pref_min=float(abs_min) if abs_min else None,
                pref_max=float(abs_max) if abs_max else None,
                opt_min=float(opt_min) if opt_min else None,
                opt_max=float(opt_max) if opt_max else None
            )
            flash(f"'{plant_name}' has been added to your urban garden!", "success")
            return redirect(url_for("plants_view"))

    plants = db.get_user_plants(user_id)
    enriched = []
    for plant in plants:
        p_data = dict(plant)
        w = weather_service.fetch_current_weather(p_data.get("city", "New Delhi"))
        p_data["watering_rec"] = weather_service.calculate_smart_watering(p_data, w)
        p_data["temp_status"] = weather_service.evaluate_plant_temperature_status(p_data, w)
        p_data["weather"] = w
        enriched.append(p_data)

    return render_template("plants.html", plants=enriched)


@app.route("/plants/<int:plant_id>/preferences", methods=["POST"])
@login_required
def update_plant_preferences(plant_id):
    """Updates editable plant-specific temperature ranges and growth stage."""
    user_id = session["user_id"]
    opt_min = request.form.get("opt_min", 18.0)
    opt_max = request.form.get("opt_max", 27.0)
    abs_min = request.form.get("abs_min", 10.0)
    abs_max = request.form.get("abs_max", 35.0)
    growth_stage = request.form.get("growth_stage", "Vegetative")
    base_watering_days = request.form.get("base_watering_days", 2)

    success = db.update_plant_preferences(
        user_id=user_id,
        plant_id=plant_id,
        opt_min=opt_min,
        opt_max=opt_max,
        abs_min=abs_min,
        abs_max=abs_max,
        growth_stage=growth_stage,
        base_watering_days=base_watering_days
    )

    if success:
        flash("Plant temperature ranges & growth stage updated successfully.", "success")
    else:
        flash("Could not update plant preferences.", "error")
    return redirect(request.referrer or url_for("plants_view"))


@app.route("/plants/<int:plant_id>/soil-moisture", methods=["POST"])
@login_required
def update_soil_moisture(plant_id):
    """Logs user-recorded soil moisture (Dry, Moderate, Moist, Wet)."""
    user_id = session["user_id"]
    moisture = request.form.get("soil_moisture", "Moderate")
    db.update_plant_soil_moisture(user_id, plant_id, moisture)
    flash(f"Soil moisture recorded as {moisture}.", "info")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/plants/<int:plant_id>/water", methods=["POST"])
@login_required
def water_plant(plant_id):
    """Logs watering event into watering_logs with user notes."""
    user_id = session["user_id"]
    moisture_before = request.form.get("soil_moisture_before", "Moderate")
    amount_ml = request.form.get("amount_ml", 500)
    notes = request.form.get("notes", "Standard morning watering")

    success = db.record_watering_event(
        user_id=user_id,
        plant_id=plant_id,
        soil_moisture_before=moisture_before,
        amount_ml=amount_ml,
        notes=notes
    )
    if success:
        flash("Watering recorded successfully! Potting soil updated to Moist.", "success")
    else:
        flash("Could not record watering.", "error")
    
    return redirect(request.referrer or url_for("plants_view"))


@app.route("/plants/<int:plant_id>/delete", methods=["POST"])
@login_required
def delete_plant(plant_id):
    user_id = session["user_id"]
    success = db.delete_user_plant(user_id, plant_id)
    if success:
        flash("Plant and associated history removed successfully.", "info")
    else:
        flash("Failed to delete plant.", "error")
    return redirect(url_for("plants_view"))


# ==================== AI Disease Detection Route ====================

@app.route("/diagnose", methods=["GET", "POST"])
@login_required
def diagnose():
    user_id = session["user_id"]
    plants = db.get_user_plants(user_id)
    result = None
    selected_plant = None

    if request.method == "POST":
        plant_id = request.form.get("plant_id")
        notes = request.form.get("notes", "").strip()

        if not plant_id:
            flash("Please select one of your plants to associate with this diagnosis.", "error")
            return render_template("diagnose.html", plants=plants)

        selected_plant = db.get_user_plant_by_id(user_id, int(plant_id))
        if not selected_plant:
            flash("Invalid plant selected.", "error")
            return render_template("diagnose.html", plants=plants)

        # Check uploaded file or sample image
        if "leaf_image" not in request.files or request.files["leaf_image"].filename == "":
            sample_choice = request.form.get("sample_image")
            if sample_choice and os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], "samples", sample_choice)):
                image_rel_path = f"uploads/samples/{sample_choice}"
                image_full_path = os.path.join(app.config["UPLOAD_FOLDER"], "samples", sample_choice)
            else:
                flash("Please upload an image of the plant leaf or select a sample image.", "error")
                return render_template("diagnose.html", plants=plants, selected_plant_id=int(plant_id))
        else:
            file = request.files["leaf_image"]
            if file and allowed_file(file.filename):
                ext = file.filename.rsplit(".", 1)[1].lower()
                unique_filename = f"leaf_{uuid.uuid4().hex[:12]}.{ext}"
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
                file.save(save_path)
                image_rel_path = f"uploads/{unique_filename}"
                image_full_path = save_path
            else:
                flash("Allowed file types: JPG, JPEG, PNG, WEBP.", "error")
                return render_template("diagnose.html", plants=plants, selected_plant_id=int(plant_id))

        # Run MobileNetV2 leaf disease classification
        diagnosis = ai_model.diagnose_leaf(image_full_path, confidence_threshold=65.0)

        if "error" in diagnosis:
            flash(diagnosis["error"], "error")
        else:
            result = diagnosis
            result["image_url"] = url_for("static", filename=image_rel_path)

            db.add_health_log(
                user_id=user_id,
                plant_id=selected_plant["id"],
                disease=result["disease_name"],
                confidence=result["confidence"],
                image_path=image_rel_path,
                symptoms=result["symptoms"],
                treatment=result["treatment"],
                prevention=result["prevention"],
                notes=notes
            )
            flash("Diagnosis complete! Results saved to your plant's health log.", "success")

    preselect_id = request.args.get("plant_id", type=int)

    return render_template(
        "diagnose.html",
        plants=plants,
        result=result,
        selected_plant=selected_plant,
        selected_plant_id=preselect_id
    )


# ==================== Health History Route ====================

@app.route("/history")
@login_required
def history():
    user_id = session["user_id"]
    plant_filter = request.args.get("plant_id", type=int)
    plants = db.get_user_plants(user_id)
    logs = db.get_user_health_logs(user_id, plant_id=plant_filter)

    return render_template(
        "history.html",
        logs=logs,
        plants=plants,
        selected_plant_id=plant_filter
    )


# ==================== Weather & Forecast Route ====================

@app.route("/weather")
@login_required
def weather_view():
    user_id = session["user_id"]
    plants = db.get_user_plants(user_id)

    query_city = request.args.get("city")
    if not query_city:
        query_city = plants[0]["city"] if plants and plants[0].get("city") else "New Delhi"

    weather = weather_service.fetch_current_weather(query_city)

    # Calculate irrigation and temperature status for all plants
    plant_schedules = []
    for plant in plants:
        p_data = dict(plant)
        p_weather = weather if p_data.get("city", "").lower() == query_city.lower() else weather_service.fetch_current_weather(p_data.get("city", query_city))
        p_data["watering_rec"] = weather_service.calculate_smart_watering(p_data, p_weather)
        p_data["temp_status"] = weather_service.evaluate_plant_temperature_status(p_data, p_weather)
        plant_schedules.append(p_data)

    return render_template(
        "weather.html",
        weather=weather,
        plants=plant_schedules,
        searched_city=query_city
    )


# ==================== Nursery & Garden Business Mode ====================

@app.route("/business")
@business_required
def business_dashboard():
    biz = g.business
    biz_id = biz["id"]
    
    kpis = db.calculate_business_kpis(biz_id)
    inventory = db.get_business_inventory(biz_id)
    low_stock_items = [it for it in inventory if it["quantity"] <= it["low_stock_threshold"]]
    batches = db.get_business_batches(biz_id)[:5]
    sales = db.get_business_sales_history(biz_id, limit=5)
    
    # Weather risks across commercial growing areas
    weather_risks = business_service.generate_business_weather_risk_summary(biz_id, city=biz.get("city", "New Delhi"))

    return render_template(
        "business/dashboard.html",
        business=biz,
        kpis=kpis,
        low_stock_items=low_stock_items,
        batches=batches,
        recent_sales=sales,
        weather_risks=weather_risks
    )


@app.route("/business/inventory", methods=["GET", "POST"])
@business_required
def business_inventory():
    biz = g.business
    biz_id = biz["id"]

    if request.method == "POST":
        plant_name = request.form.get("plant_name", "").strip()
        species = request.form.get("species", "").strip()
        category = request.form.get("category", "Vegetable").strip()
        quantity = int(request.form.get("quantity", 0))
        threshold = int(request.form.get("low_stock_threshold", 5))
        cost = float(request.form.get("purchase_cost", 0.0))
        price = float(request.form.get("selling_price", 0.0))
        supplier = request.form.get("supplier", "").strip()
        location_zone = request.form.get("location_zone", "Greenhouse A").strip()
        health_status = request.form.get("health_status", "Healthy").strip()
        notes = request.form.get("notes", "").strip()

        if plant_name:
            db.add_inventory_item(
                biz_id=biz_id,
                plant_name=plant_name,
                species=species,
                category=category,
                quantity=quantity,
                low_stock_threshold=threshold,
                purchase_cost=cost,
                selling_price=price,
                supplier=supplier,
                location_zone=location_zone,
                health_status=health_status,
                notes=notes
            )
            flash(f"'{plant_name}' added to nursery inventory.", "success")
            return redirect(url_for("business_inventory"))

    # Search & filters
    category_filter = request.args.get("category", "All")
    search_query = request.args.get("search", "")
    low_stock_only = request.args.get("low_stock") == "1"

    items = db.get_business_inventory(
        biz_id=biz_id,
        category=category_filter,
        search=search_query,
        low_stock_only=low_stock_only
    )
    kpis = db.calculate_business_kpis(biz_id)

    return render_template(
        "business/inventory.html",
        business=biz,
        items=items,
        kpis=kpis,
        category_filter=category_filter,
        search_query=search_query,
        low_stock_only=low_stock_only
    )


@app.route("/business/inventory/<int:item_id>/adjust", methods=["POST"])
@business_required
def business_adjust_stock(item_id):
    biz = g.business
    user_id = session["user_id"]
    movement_type = request.form.get("movement_type", "Sale")
    quantity = int(request.form.get("quantity", 1))
    unit_price = request.form.get("unit_price")
    notes = request.form.get("notes", "").strip()

    price_val = float(unit_price) if unit_price else None

    success, err = db.adjust_inventory_stock(
        biz_id=biz["id"],
        user_id=user_id,
        item_id=item_id,
        movement_type=movement_type,
        quantity_change=quantity,
        unit_price=price_val,
        notes=notes
    )

    if success:
        flash(f"Stock successfully adjusted ({movement_type}: {quantity} units).", "success")
    else:
        flash(err or "Failed to adjust stock.", "error")

    return redirect(request.referrer or url_for("business_inventory"))


@app.route("/business/batches", methods=["GET", "POST"])
@business_required
def business_batches():
    biz = g.business
    biz_id = biz["id"]

    if request.method == "POST":
        batch_name = request.form.get("batch_name", "").strip()
        plant_type = request.form.get("plant_type", "Tomato").strip()
        growing_area = request.form.get("growing_area", "Greenhouse A").strip()
        quantity = int(request.form.get("quantity", 25))
        health_status = request.form.get("health_status", "Good").strip()

        if batch_name:
            db.add_plant_batch(biz_id, batch_name, plant_type, growing_area, quantity, health_status)
            flash(f"Commercial plant batch '{batch_name}' registered.", "success")
            return redirect(url_for("business_batches"))

    batches = db.get_business_batches(biz_id)
    return render_template("business/batches.html", business=biz, batches=batches)


@app.route("/business/batches/<int:batch_id>/review", methods=["POST"])
@business_required
def business_review_batch(batch_id):
    biz = g.business
    status = request.form.get("health_status", "Good")
    notes = request.form.get("review_notes", "").strip()

    db.review_plant_batch(biz["id"], batch_id, status, notes)
    flash("Batch inspection review recorded by manager.", "success")
    return redirect(url_for("business_batches"))


@app.route("/business/care-cards")
@business_required
def business_care_cards():
    biz = g.business
    selected_crop = request.args.get("crop", "Tomato")
    plant_name = request.args.get("name")
    
    card_data = business_service.get_care_guide_for_plant(selected_crop, plant_name=plant_name)
    inventory_items = db.get_business_inventory(biz["id"])

    return render_template(
        "business/care_cards.html",
        business=biz,
        card=card_data,
        selected_crop=selected_crop,
        inventory_items=inventory_items
    )


@app.route("/business/reports")
@business_required
def business_reports():
    biz = g.business
    kpis = db.calculate_business_kpis(biz["id"])
    sales = db.get_business_sales_history(biz["id"], limit=20)
    inventory = db.get_business_inventory(biz["id"])

    return render_template(
        "business/reports.html",
        business=biz,
        kpis=kpis,
        sales=sales,
        inventory=inventory
    )


@app.route("/business/reports/export")
@business_required
def business_export_report():
    """Generates real-time downloadable CSV business reports."""
    biz = g.business
    biz_id = biz["id"]
    report_type = request.args.get("type", "inventory")
    date_tag = datetime.now().strftime("%Y%m%d")

    if report_type == "low_stock":
        csv_data = business_service.export_low_stock_csv(biz_id)
        filename = f"low_stock_report_{date_tag}.csv"
    elif report_type == "batches":
        csv_data = business_service.export_batch_health_csv(biz_id)
        filename = f"batch_health_report_{date_tag}.csv"
    elif report_type == "sales":
        csv_data = business_service.export_sales_csv(biz_id)
        filename = f"sales_summary_{date_tag}.csv"
    else: # default inventory
        csv_data = business_service.export_inventory_csv(biz_id)
        filename = f"nursery_inventory_{date_tag}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# API endpoint for dynamic weather data
@app.route("/api/weather")
@login_required
def api_weather():
    city = request.args.get("city", "New Delhi")
    data = weather_service.fetch_current_weather(city)
    return jsonify(data)


if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))
    app.run(host=host, port=port, debug=True)
