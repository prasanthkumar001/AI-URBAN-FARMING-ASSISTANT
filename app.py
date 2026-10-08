"""
AI Urban Farming Assistant - Main Flask Application.
Provides secure authentication, user data isolation, MobileNetV2 leaf disease
classification, and Open-Meteo smart watering recommendations.
"""

import os
import uuid
from functools import wraps
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, send_from_directory
)
from werkzeug.utils import secure_filename

import database as db
import ai_model
import weather_service

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "urban-farming-secret-key-2026-secure-salt-9812")

# Uploads directory
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max image size

# Initialize database tables on startup
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


@app.context_processor
def inject_user():
    """Inject logged-in user into templates globally."""
    user = None
    if "user_id" in session:
        user = {
            "id": session["user_id"],
            "username": session.get("username"),
            "email": session.get("email")
        }
    return dict(current_user=user, current_year=datetime.now().year)


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

        # Password confirmation validation
        if password != confirm_password:
            flash("Passwords do not match. Please re-enter both passwords.", "error")
            return render_template("auth/register.html", username=username, email=email)

        # Register in database with secure scrypt hashing
        user_id, error = db.register_user(username, email, password)
        if error:
            flash(error, "error")
            return render_template("auth/register.html", username=username, email=email)

        # Successful registration - log the user in directly
        session["user_id"] = user_id
        session["username"] = username
        session["email"] = email
        flash(f"Welcome to Urban Farming Assistant, {username}! Your account has been created successfully.", "success")
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

        # Session setup
        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["email"] = user["email"]
        flash(f"Welcome back, {user['username']}!", "success")
        return redirect(next_target)

    return render_template("auth/login.html", next=next_page)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been safely logged out.", "info")
    return redirect(url_for("login"))


# ==================== Core Application Routes ====================

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

    # Fetch weather for the user's primary plant location or default city
    primary_city = plants[0]["city"] if plants and plants[0].get("city") else "New Delhi"
    weather = weather_service.fetch_current_weather(primary_city)

    # Compute smart watering recommendations for each plant
    plants_with_watering = []
    urgent_water_count = 0
    
    for plant in plants:
        p_data = dict(plant)
        p_weather = weather if p_data.get("city") == primary_city else weather_service.fetch_current_weather(p_data.get("city", "New Delhi"))
        watering_rec = weather_service.calculate_smart_watering(
            plant_type=p_data["plant_type"],
            base_watering_days=p_data["base_watering_days"],
            last_watered_date=p_data["last_watered_date"],
            location_type=p_data["location_type"],
            weather_data=p_weather
        )
        p_data["watering_rec"] = watering_rec
        if watering_rec["status"] == "Water today":
            urgent_water_count += 1
        plants_with_watering.append(p_data)

    return render_template(
        "dashboard.html",
        plants=plants_with_watering,
        recent_logs=recent_logs,
        weather=weather,
        total_plants=len(plants),
        urgent_water_count=urgent_water_count
    )


@app.route("/plants", methods=["GET", "POST"])
@login_required
def plants_view():
    user_id = session["user_id"]

    if request.method == "POST":
        plant_name = request.form.get("plant_name", "").strip()
        plant_type = request.form.get("plant_type", "").strip()
        location_type = request.form.get("location_type", "Balcony").strip()
        city = request.form.get("city", "New Delhi").strip()
        planting_date = request.form.get("planting_date", datetime.now().strftime("%Y-%m-%d")).strip()
        base_watering_days = int(request.form.get("base_watering_days", 2))
        notes = request.form.get("notes", "").strip()

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
                notes=notes
            )
            flash(f"'{plant_name}' has been added to your urban garden!", "success")
            return redirect(url_for("plants_view"))

    plants = db.get_user_plants(user_id)
    # Enrich with watering recommendations
    enriched_plants = []
    for plant in plants:
        p_data = dict(plant)
        w = weather_service.fetch_current_weather(p_data.get("city", "New Delhi"))
        p_data["watering_rec"] = weather_service.calculate_smart_watering(
            p_data["plant_type"],
            p_data["base_watering_days"],
            p_data["last_watered_date"],
            p_data["location_type"],
            w
        )
        p_data["weather"] = w
        enriched_plants.append(p_data)

    return render_template("plants.html", plants=enriched_plants)


@app.route("/plants/<int:plant_id>/water", methods=["POST"])
@login_required
def water_plant(plant_id):
    user_id = session["user_id"]
    success = db.update_plant_watering(user_id, plant_id)
    if success:
        flash("Plant marked as watered today! Soil moisture updated.", "success")
    else:
        flash("Could not update plant watering status.", "error")
    
    redirect_to = request.referrer or url_for("plants_view")
    return redirect(redirect_to)


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

        # Check uploaded file
        if "leaf_image" not in request.files or request.files["leaf_image"].filename == "":
            # Check if user selected one of the sample leaf images
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

        # Run MobileNetV2 diagnosis
        diagnosis = ai_model.diagnose_leaf(image_full_path, confidence_threshold=65.0)

        if "error" in diagnosis:
            flash(diagnosis["error"], "error")
        else:
            result = diagnosis
            result["image_url"] = url_for("static", filename=image_rel_path)

            # Record in user-specific health_logs database table
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

    # Check for query param to pre-select plant
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


# ==================== Weather & Smart Watering Route ====================

@app.route("/weather")
@login_required
def weather_view():
    user_id = session["user_id"]
    plants = db.get_user_plants(user_id)

    # City query or user plant's city or default
    query_city = request.args.get("city")
    if not query_city:
        query_city = plants[0]["city"] if plants and plants[0].get("city") else "New Delhi"

    weather = weather_service.fetch_current_weather(query_city)

    # Calculate irrigation status for all user plants under this weather
    plant_schedules = []
    for plant in plants:
        p_data = dict(plant)
        p_weather = weather if p_data.get("city", "").lower() == query_city.lower() else weather_service.fetch_current_weather(p_data.get("city", query_city))
        rec = weather_service.calculate_smart_watering(
            plant_type=p_data["plant_type"],
            base_watering_days=p_data["base_watering_days"],
            last_watered_date=p_data["last_watered_date"],
            location_type=p_data["location_type"],
            weather_data=p_weather
        )
        p_data["watering_rec"] = rec
        plant_schedules.append(p_data)

    return render_template(
        "weather.html",
        weather=weather,
        plants=plant_schedules,
        searched_city=query_city
    )


# API endpoint for dynamic weather data
@app.route("/api/weather")
@login_required
def api_weather():
    city = request.args.get("city", "New Delhi")
    data = weather_service.fetch_current_weather(city)
    return jsonify(data)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
