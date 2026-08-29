# -------- Imports --------
from dotenv import load_dotenv
load_dotenv()

import datetime
import json
import math
import requests
import os
import re
from difflib import get_close_matches

from flask import Flask, jsonify, render_template, request, session
from flask_cors import CORS
from flask_mysqldb import MySQL
from werkzeug.security import check_password_hash, generate_password_hash

# -------- AI Modules --------
from itinerary import generate_itinerary
from ml_model import (
    build_user_item_matrix,
    get_recommendations,
    train_model
)
from nlp import process_query

# -------- Flask Config --------
app = Flask(__name__)
CORS(app)

# -------- Secret Key --------
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "ai-travel-planner-dev-secret"
)

# -------- MySQL Config --------
app.config["MYSQL_HOST"] = os.getenv(
    "MYSQL_HOST",
    "127.0.0.1"
)

app.config["MYSQL_USER"] = os.getenv(
    "MYSQL_USER",
    "root"
)

app.config["MYSQL_PASSWORD"] = os.getenv(
    "MYSQL_PASSWORD",
    ""
)

app.config["MYSQL_DB"] = os.getenv(
    "MYSQL_DB",
    "travel_app"
)


# -------- MySQL Initialize --------
mysql = MySQL(app)

# -------- API Keys --------
WEATHER_API_KEY = os.getenv(
    "OPENWEATHER_API_KEY",
    ""
)

GOOGLE_MAPS_API_KEY = os.getenv(
    "GOOGLE_MAPS_API_KEY",
    ""
)

GOOGLE_CLIENT_ID = os.getenv(
    "GOOGLE_CLIENT_ID",
    ""
).strip()

# -------- Static Advisories  for different city --------
STATIC_ADVISORIES = {

    "hunza": {
        "warning": "Mountain roads can be slow after rain or snowfall.",
        "tips": [
            "Carry a light jacket even in summer evenings.",
            "Keep cash available because small shops may not accept cards.",
            "Start road trips early to avoid late-night mountain driving.",
        ],
    },

    "skardu": {
        "warning": "Weather changes quickly and some routes may close without notice.",
        "tips": [
            "Confirm hotel and transport bookings in advance.",
            "Keep power banks and offline maps ready.",
            "Drink plenty of water while adjusting to altitude.",
        ],
    },

    "murree": {
        "warning": "Weekend traffic can be heavy during peak season.",
        "tips": [
            "Travel on weekdays for a smoother trip.",
            "Book parking-aware accommodation if driving.",
            "Pack warm layers for late evenings.",
        ],
    },

    "gwadar": {
        "warning": "Daytime heat can be intense and services may be spread out.",
        "tips": [
            "Carry water and sun protection throughout the day.",
            "Plan fuel stops ahead of longer drives.",
            "Prefer early morning or evening beach visits.",
        ],
    },
}

# These aliases cover popular search words that are valid travel inputs but may not
# exist as exact destination rows in the database. For example, Islamabad visitors
# usually want nearby trip options like Murree or Taxila-style Punjab trips.
DESTINATION_SEARCH_ALIASES = {
    "islamabad": ["murree", "taxila", "punjab"],
    "islamabadcapitalterritory": ["murree", "taxila", "punjab"],
    "northern areas": ["gilgit baltistan", "hunza", "skardu", "swat", "valley", "mountain", "trekking"],
    "north pakistan": ["gilgit baltistan", "hunza", "skardu", "swat", "valley", "mountain", "trekking"],
    "northern pakistan": ["gilgit baltistan", "hunza", "skardu", "swat", "valley", "mountain", "trekking"],
    "hunza valley": ["hunza", "gilgit baltistan", "valley"],
    "gwadar beach": ["gwadar", "balochistan", "beach"],
    "swat valley": ["swat", "khyber pakhtunkhwa", "valley"],
}

FALLBACK_RESTAURANTS = {
    # Local fallback data keeps restaurant pages useful when the database/API is empty.
    "swat": [
        {"id": None, "name": "Swat Serena Restaurant", "city": "Swat", "rating": 4.5, "type": "Pakistani", "price": 1800, "source": "fallback"},
        {"id": None, "name": "Malam Jabba Cafe", "city": "Swat", "rating": 4.3, "type": "Cafe", "price": 1200, "source": "fallback"},
        {"id": None, "name": "Mingora Food Court", "city": "Swat", "rating": 4.2, "type": "Local Food", "price": 1000, "source": "fallback"},
    ],
    
    "murree": [
        {"id": None, "name": "Mall Road Cafe", "city": "Murree", "rating": 4.3, "type": "Cafe", "price": 1200, "source": "fallback"},
        {"id": None, "name": "Murree Brew Restaurant", "city": "Murree", "rating": 4.2, "type": "Pakistani", "price": 1500, "source": "fallback"},
        {"id": None, "name": "Pine View Restaurant", "city": "Murree", "rating": 4.1, "type": "Continental", "price": 1800, "source": "fallback"},
        {"id": None, "name": "Bhurban Dining Hall", "city": "Murree", "rating": 4.0, "type": "Buffet", "price": 2000, "source": "fallback"},
    ],
    "gwadar": [
        {"id": None, "name": "Coastal Kitchen", "city": "Gwadar", "rating": 4.4, "type": "Seafood", "price": 2200, "source": "fallback"},
        {"id": None, "name": "Pearl Continental Gwadar", "city": "Gwadar", "rating": 4.5, "type": "Continental", "price": 3000, "source": "fallback"},
        {"id": None, "name": "Port View Cafe", "city": "Gwadar", "rating": 4.0, "type": "Cafe", "price": 1000, "source": "fallback"},
    ],
}

FALLBACK_EVENTS = {
    # A small built-in event list makes the demo feel alive even before admin data is added.
    "swat": [
        {"id": None, "name": "Swat Summer Festival", "city": "Swat", "event_date": "2026-07-20", "description": "Local food, handicrafts, music, and family activities.", "is_upcoming": True},
        {"id": None, "name": "Malam Jabba Snow Festival", "city": "Swat", "event_date": "2026-12-28", "description": "Winter sports, food stalls, and mountain sightseeing.", "is_upcoming": True},
    ],
}

# -------- Weather Route --------
@app.route("/weather/<city>")
def fetch_weather(city):

    try:

        # OpenWeatherMap works better with known city names, so tourist spots are mapped first.
        city_mapping = {
            "hunza": "Gilgit,PK",
            "hunza valley": "Gilgit,PK",
            "fairy meadows": "Gilgit,PK",
            "naltar": "Gilgit,PK",
            "skardu": "Skardu,PK",
            "murree": "Murree,PK",
            "swat": "Mingora,PK",
            "swat valley": "Mingora,PK",
            "naran": "Naran,PK",
            "kaghan": "Kaghan,PK",
            "gwadar": "Gwadar,PK",
            "gwadar beach": "Gwadar,PK",
            "karachi": "Karachi,PK"
        }

        requested_city = (city or "").strip()
        normalized_city = normalize_city_key(requested_city)
        destination = get_destination_record_by_name(requested_city)
        search_city = city_mapping.get(normalized_city, requested_city)

        # If no API key is configured, the frontend still receives a friendly profile-based answer.
        if not weather_enabled():
            return jsonify({
                "temperature": None,
                "humidity": None,
                "weather": destination.get("weather") if destination else "Unavailable",
                "source": "destination_profile",
                "resolved_city": destination.get("name") if destination else requested_city,
                "message": "OpenWeatherMap API key is not configured."
            })

        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": search_city, "appid": WEATHER_API_KEY, "units": "metric"},
            timeout=8,
        )

        data = response.json()
        print("Weather API Response:", data)

        # Non-200 responses are handled as soft failures so the page does not break for users.
        if response.status_code != 200:

            return jsonify({
                "temperature": None,
                "humidity": None,
                "weather": destination.get("weather") if destination else "Unavailable",
                "source": "destination_profile",
                "resolved_city": destination.get("name") if destination else search_city,
                "message": "Live weather was unavailable, so destination profile weather is shown."
            })

        return jsonify({

            "temperature": data["main"]["temp"],

            "humidity": data["main"]["humidity"],

            "weather": data["weather"][0]["description"],

            "source": "OpenWeatherMap",

            "resolved_city": search_city,

            "icon": data["weather"][0]["icon"],

            "feels_like": data["main"]["feels_like"]
        })

    except (requests.RequestException, ValueError, KeyError, TypeError) as e:

        # Network/API parsing errors also fall back to destination profile weather.
        requested_city = (city or "").strip()
        destination = get_destination_record_by_name(requested_city)

        return jsonify({
            "temperature": None,
            "humidity": None,
            "weather": destination.get("weather") if destination else "Unavailable",
            "source": "destination_profile" if destination else "fallback",
            "resolved_city": destination.get("name") if destination else requested_city,
            "message": "Live weather was unavailable, so destination profile weather is shown."
        })

# -------- Helpers --------

# Shared helper functions used by several routes

# This function returns a database cursor for running queries
def get_cursor():
    return mysql.connection.cursor()


# This function returns a standard error response in JSON format
def json_error(message, status_code=400):
    return jsonify({"error": message}), status_code

# This function safely receives JSON data from frontend requests

def get_json_payload():
    """Return request JSON payload as a dictionary."""
    return request.get_json(silent=True) or {}


# This function checks whether the weather API is configured or not
def weather_enabled():
    return bool((WEATHER_API_KEY or "").strip())

# This function automatically creates required database tables

def ensure_feature_tables():
    cur = get_cursor()
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS weather_cache (
                city VARCHAR(100) PRIMARY KEY,
                temperature FLOAT,
                description VARCHAR(100),
                humidity INT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS restaurants (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                city VARCHAR(100) NOT NULL,
                rating DECIMAL(2,1) DEFAULT 4.0,
                type VARCHAR(50),
                price INT DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                city VARCHAR(100) NOT NULL,
                event_date DATE NOT NULL,
                description TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_plans (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                destination_id INT NOT NULL,
                itinerary LONGTEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (destination_id) REFERENCES destinations(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        ensure_feedback_schema(cur)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS advisories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                city VARCHAR(100) UNIQUE,
                warning TEXT,
                tips TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_models (
                id INT AUTO_INCREMENT PRIMARY KEY,
                model_name VARCHAR(100) UNIQUE,
                status ENUM('active','inactive') DEFAULT 'inactive'
            )
            """
        )
        cur.execute(
            """
            INSERT INTO ai_models (model_name, status)
            VALUES ('Content-Based Recommender', 'inactive')
            ON DUPLICATE KEY UPDATE model_name=VALUES(model_name)
            """
        )

        cur.execute("SELECT COUNT(*) FROM restaurants")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                """
                INSERT INTO restaurants (name, city, rating, type, price)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [
                    ("Cafe De Hunza", "Hunza", 4.5, "Cafe", 1500),
                    ("Mountain Taste", "Hunza", 4.4, "Pakistani", 1800),
                    ("Skardu Grill", "Skardu", 4.4, "BBQ", 1800),
                    ("Mall Road Bites", "Murree", 4.3, "Fast Food", 1200),
                    ("Coastal Kitchen", "Gwadar", 4.2, "Seafood", 2200),
                ],
            )

        cur.execute("SELECT COUNT(*) FROM events")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                """
                INSERT INTO events (name, city, event_date, description)
                VALUES (%s, %s, %s, %s)
                """,
                [
                    ("Hunza Cultural Night", "Hunza", "2026-06-15", "Traditional food, local music and handicrafts."),
                    ("Skardu Spring Festival", "Skardu", "2026-05-20", "Seasonal performances and family activities."),
                    ("Murree Winter Gala", "Murree", "2026-12-10", "Snow activities, food stalls and live performances."),
                    ("Gwadar Coastal Festival", "Gwadar", "2026-11-05", "Beachfront community event with local art and seafood."),
                ],
            )

        mysql.connection.commit()
    except Exception:
        mysql.connection.rollback()
        raise
    finally:
        cur.close()

# This function fetches all column names from a database table

def get_table_columns(cur, table_name):
    # MySQL returns one row per column; this lets us safely upgrade old tables.
    cur.execute(f"SHOW COLUMNS FROM {table_name}")
    return {row[0] for row in cur.fetchall()}


# This function upgrades old feedback table structure safely

def ensure_feedback_schema(cur):
    # Some older project databases created feedback without created_at/message.
    # We migrate gently so existing feedback rows are preserved for the admin panel.
    columns = get_table_columns(cur, "feedback")

    if "created_at" not in columns:
        cur.execute(
            """
            ALTER TABLE feedback
            ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """
        )
        columns.add("created_at")

    if "user_id" not in columns:
        cur.execute("ALTER TABLE feedback ADD COLUMN user_id INT NULL")
        columns.add("user_id")

    if "message" not in columns and "feedback" in columns:
        cur.execute("ALTER TABLE feedback ADD COLUMN message TEXT")
        cur.execute("UPDATE feedback SET message=feedback WHERE message IS NULL")
        columns.add("message")

    if "feedback" not in columns and "message" in columns:
        cur.execute("ALTER TABLE feedback ADD COLUMN feedback TEXT")
        cur.execute("UPDATE feedback SET feedback=message WHERE feedback IS NULL")


# This function prepares itinerary data before saving it in the database.
def serialize_itinerary(itinerary):
    if isinstance(itinerary, (list, dict)):
        return json.dumps(itinerary)
    return str(itinerary or "").strip()


# This function restores saved itinerary text back into list/dictionary form when possible.
def deserialize_itinerary(itinerary):
    if not itinerary:
        return []

    try:
        parsed = json.loads(itinerary)
        return parsed
    except (TypeError, ValueError, json.JSONDecodeError):
        return itinerary


# This function checks whether a local static image path actually exists.
def static_image_exists(image_path):
    if not image_path or not str(image_path).startswith("/static/"):
        return bool(image_path)

    relative_path = str(image_path).lstrip("/").replace("/", os.sep)
    return os.path.exists(os.path.join(os.path.dirname(__file__), relative_path))


# This function prevents mismatched destination cards from showing the wrong city image.
def image_path_matches_destination(name, image_path):
    if not image_path:
        return False

    destination_key = normalize_city_key(name)
    image_name = os.path.splitext(os.path.basename(str(image_path).lower()))[0]
    image_key = normalize_city_key(image_name.replace("-", " ").replace("_", " "))
    known_image_owners = {
        "hunza": {"hunza"},
        "lahore": {"lahore"},
        "murree": {"murree"},
        "skardu": {"skardu"},
        "gawadar": {"gwadar"},
        "gwadar": {"gwadar"},
        "swat jgp": {"swat"},
        "swat": {"swat"},
    }

    owners = known_image_owners.get(image_key)
    if owners:
        return destination_key in owners or any(owner in destination_key for owner in owners)

    return image_key and (image_key in destination_key or destination_key in image_key)


# This function chooses the best available image for a destination card.
def resolve_destination_image(name, image_path):
    if static_image_exists(image_path) and image_path_matches_destination(name, image_path):
        return image_path

    destination_key = normalize_city_key(name)
    # These names use known filenames that may not match the exact database spelling.
    known_images = {
        "gwadar": "/static/images/gawadar.jpg",
        "gwadar beach": "/static/images/gawadar.jpg",
        "swat": "/static/images/swat.jpeg",
        "swat valley": "/static/images/swat.jpeg",
    }

    candidates = []
    if destination_key in known_images:
        candidates.append(known_images[destination_key])

    slug = destination_key.replace(" ", "-")
    candidates.extend(
        [
            f"/static/images/{slug}.jpg",
            f"/static/images/{slug}.jpeg",
            f"/static/images/{slug}.png",
            f"/static/images/{str(name or '').strip()}.jpg",
            f"/static/images/{str(name or '').strip()}.jpeg",
            f"/static/images/{str(name or '').strip()}.png",
        ]
    )

    for candidate in candidates:
        if static_image_exists(candidate):
            return candidate

    return ""


# This function formats database row into destination dictionary
def format_destination(row):
    if not row:
        return {}

    # The project has used more than one destinations table layout, so both are supported.
    current_schema = (
        "id", "name", "type", "region", "cost", "weather", "best_season",
        "activities", "tags", "safety_rating", "user_rating", "image",
        "hotel_cost_per_day", "meal_cost_per_day", "travel_cost",
        "latitude", "longitude",
    )
    legacy_schema = (
        "id", "name", "type", "region", "cost", "weather", "best_season",
        "activities", "safety_rating", "user_rating", "image",
        "hotel_cost_per_day", "meal_cost_per_day", "travel_cost",
    )
    schema = current_schema if len(row) >= len(current_schema) else legacy_schema
    row_data = {field: row[index] if index < len(row) else None for index, field in enumerate(schema)}

    name = row_data.get("name") or "Unknown Destination"
    image = resolve_destination_image(name, row_data.get("image"))

    return {
        "id": row_data.get("id"),
        "name": name,
        "type": row_data.get("type") or "Destination",
        "region": row_data.get("region") or "Pakistan",
        "cost": row_data.get("cost") or 0,
        "weather": row_data.get("weather") or "Unavailable",
        "best_season": row_data.get("best_season") or "Not specified",
        "activities": row_data.get("activities") or "",
        "tags": row_data.get("tags") or "",
        "safety_rating": row_data.get("safety_rating") or 0,
        "user_rating": row_data.get("user_rating") or 0,
        "image": image,
        "hotel_cost_per_day": row_data.get("hotel_cost_per_day") or 0,
        "meal_cost_per_day": row_data.get("meal_cost_per_day") or 0,
        "travel_cost": row_data.get("travel_cost") or 0,
        "latitude": row_data.get("latitude"),
        "longitude": row_data.get("longitude"),
    }

# This function fetches all destinations from the database

def fetch_all_destinations():
    cur = get_cursor()
    try:
        cur.execute("SELECT * FROM destinations")
        rows = cur.fetchall()
        if not rows:
            # # ADDED FEATURE: Load from destinations.json if DB empty
            load_destinations_from_json()
            cur.execute("SELECT * FROM destinations")
            rows = cur.fetchall()
        return [format_destination(row) for row in rows]
    finally:
        cur.close()
# This function creates searchable text from destination data

def destination_search_text(destination):
    # This text is used for simple case-insensitive search across useful fields.
    searchable_fields = (
        "name",
        "type",
        "region",
        "weather",
        "best_season",
        "activities",
        "tags",
    )
    return " ".join(str(destination.get(field, "")) for field in searchable_fields).lower()


def get_search_terms(query):
    # Build exact, normalized and alias terms from the user's search text.
    clean_query = normalize_place_name(query)
    city_key = normalize_city_key(clean_query)
    terms = [clean_query, city_key]

    for alias, alias_terms in DESTINATION_SEARCH_ALIASES.items():
        alias_key = normalize_city_key(alias)
        if clean_query == alias_key or clean_query in alias_key or alias_key in clean_query:
            terms.extend(alias_terms)

    return list(dict.fromkeys(term for term in terms if term))


# This function checks whether one search term belongs to a destination profile.
def destination_matches_term(destination, term):
    destination_text = destination_search_text(destination)
    normalized_term = normalize_city_key(term)
    destination_name = normalize_city_key(destination.get("name"))

    if normalized_term in destination_text:
        return True

    if normalized_term and (
        normalized_term in destination_name
        or destination_name in normalized_term
    ):
        return True

    return False


# These keyword groups help natural language searches map feelings to destination data.
TRAVEL_QUERY_KEYWORDS = {
    "honeymoon": ["honeymoon", "romantic", "couple", "relaxing", "scenic"],
    "relaxing": ["relaxing", "relax", "peaceful", "scenic", "nature", "lake", "beach"],
    "relaxation": ["relaxing", "relax", "peaceful", "scenic", "nature", "lake", "beach"],
    "beach": ["beach", "coastal", "sea", "seafood", "snorkeling", "fishing"],
    "family": ["family", "picnics", "shopping", "weekend", "safe"],
    "adventure": ["adventure", "trekking", "hiking", "camping", "rafting", "mountain"],
    "luxury": ["luxury", "resort", "hotel", "scenic"],
    "budget": ["budget", "cheap", "affordable"],
    "cheap": ["budget", "cheap", "affordable"],
    "affordable": ["budget", "cheap", "affordable"],
    "cold": ["cold", "winter", "mountain", "hill station", "lake"],
    "mountain": ["mountain", "mountains", "trekking", "hiking", "camping"],
    "mountains": ["mountain", "mountains", "trekking", "hiking", "camping"],
}

# Small words are ignored so "show me a beach trip" focuses on "beach".
QUERY_STOPWORDS = {
    "a", "an", "and", "are", "at", "best", "destination", "destinations",
    "find", "for", "give", "i", "in", "is", "me", "of", "or", "place",
    "places", "please", "show", "suggest", "the", "to", "travel", "trip",
    "want", "with",
}


# This function extracts useful travel words from a sentence typed by the user.
def get_natural_language_terms(query):
    lowered_query = normalize_place_name(query)
    terms = []

    if "cold weather" in lowered_query:
        terms.extend(["cold", "winter", "mountain", "hill station"])

    for token in re.findall(r"[a-z]+", lowered_query):
        if token in QUERY_STOPWORDS:
            continue
        terms.append(token)
        terms.extend(TRAVEL_QUERY_KEYWORDS.get(token, []))

    return list(dict.fromkeys(term for term in terms if term))


# This function scores destinations for conversational searches such as "cold mountain trip".
def natural_language_destination_matches(query, destinations, limit=6):
    terms = get_natural_language_terms(query)
    if not terms:
        return []

    original_terms = {
        token for token in re.findall(r"[a-z]+", normalize_place_name(query))
        if token not in QUERY_STOPWORDS
    }
    scored_matches = []
    for destination in destinations:
        searchable_text = destination_search_text(destination)
        score = 0

        # Stronger fields get more weight so exact place/type matches rise to the top.
        for term in terms:
            normalized_term = normalize_city_key(term)
            if not normalized_term:
                continue
            if normalized_term in normalize_city_key(destination.get("name")):
                score += 8
            if normalized_term in str(destination.get("type", "")).lower():
                score += 6
            if normalized_term in str(destination.get("tags", "")).lower():
                score += 5
            if normalized_term in str(destination.get("activities", "")).lower():
                score += 4
            if normalized_term in str(destination.get("region", "")).lower():
                score += 3
            if normalized_term in searchable_text:
                score += 1
            if normalized_term in original_terms and normalized_term in searchable_text:
                score += 8

        if "beach" in original_terms:
            score += 20 if "beach" in searchable_text or "coastal" in searchable_text else -12
        if "mountains" in original_terms or "mountain" in original_terms:
            score += 16 if "mountain" in searchable_text or "hill station" in searchable_text else -8
        if "cold" in original_terms:
            score += 12 if "cold" in searchable_text else -4

        if "budget" in terms or "cheap" in terms or "affordable" in terms:
            score += max(0, 5 - int((destination.get("cost") or 0) / 10000))

        if score > 0:
            scored_matches.append((score, destination.get("user_rating") or 0, destination))

    scored_matches.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [destination for _, _, destination in scored_matches[:limit]]

# This function finds similar destinations even with spelling mistakes

def fuzzy_destination_matches(query, destinations):
    # Fuzzy matching catches small spelling differences without making random text match.
    clean_query = normalize_city_key(query)
    if not clean_query:
        return []

    name_lookup = {
        normalize_city_key(destination.get("name")): destination
        for destination in destinations
        if destination.get("name")
    }
    matches = get_close_matches(clean_query, list(name_lookup.keys()), n=5, cutoff=0.68)
    return [name_lookup[match] for match in matches]


def search_destinations(query):
    # Search is deterministic first, then fuzzy. This keeps invalid words empty while
    # still accepting real city names, aliases and partial destination names.
    clean_query = normalize_place_name(query)
    if not clean_query:
        return []

    destinations = fetch_all_destinations()
    matches = []
    seen_ids = set()

    # First try the user's actual words. This keeps "Hunza valley" focused on Hunza
    # instead of widening immediately to all Gilgit Baltistan destinations.
    direct_terms = list(dict.fromkeys([clean_query, normalize_city_key(clean_query)]))
    for destination in destinations:
        if any(destination_matches_term(destination, term) for term in direct_terms):
            destination_id = destination.get("id")
            if destination_id not in seen_ids:
                seen_ids.add(destination_id)
                matches.append(destination)

    if matches:
        return matches

    # If no direct destination exists, expand valid aliases like Islamabad or northern areas.
    search_terms = get_search_terms(clean_query)
    for destination in destinations:
        if any(destination_matches_term(destination, term) for term in search_terms):
            destination_id = destination.get("id")
            if destination_id not in seen_ids:
                seen_ids.add(destination_id)
                matches.append(destination)

    if not matches:
        matches = fuzzy_destination_matches(clean_query, destinations)

    if not matches:
        matches = natural_language_destination_matches(clean_query, destinations)

    return matches


# This function loads destinations from JSON into the database
def load_destinations_from_json():
    import json
    try:
        with open('destinations.json', 'r') as f:
            destinations = json.load(f)
        cur = get_cursor()
        try:
            for dest in destinations:
                cur.execute("""
                    INSERT INTO destinations (id, name, type, region, cost, weather, best_season, activities, safety_rating, user_rating, hotel_cost_per_day, meal_cost_per_day, travel_cost)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE name=VALUES(name)
                """, (
                    dest['id'], dest['name'], dest['type'], dest['region'], dest['cost'], dest['weather'], dest['best_season'], dest['activities'],
                    dest['safety_rating'], dest['user_rating'], dest['hotel_cost_per_day'], dest['meal_cost_per_day'], dest['travel_cost']
                ))
            mysql.connection.commit()
        finally:
            cur.close()
    except Exception as e:
        print(f"Error loading destinations: {e}")


# This function normalizes place names for better matching
def normalize_place_name(value):
    return " ".join(str(value or "").strip().lower().split())


# This function calculates distance between two locations
def haversine_distance_km(lat1, lng1, lat2, lng2):
    earth_radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    haversine_a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    haversine_c = 2 * math.atan2(math.sqrt(haversine_a), math.sqrt(1 - haversine_a))
    return earth_radius_km * haversine_c


# This function loads destination coordinates from JSON file
def load_destination_coordinate_lookup():
    coordinates_by_name = {}
    try:
        json_path = os.path.join(os.path.dirname(__file__), "destinations.json")
        with open(json_path, "r", encoding="utf-8") as file:
            json_destinations = json.load(file)

        for destination in json_destinations:
            destination_key = normalize_place_name(destination.get("name"))
            destination_lat = destination.get("latitude")
            destination_lng = destination.get("longitude")
            if destination_key and destination_lat is not None and destination_lng is not None:
                coordinates_by_name[destination_key] = (float(destination_lat), float(destination_lng))
    except Exception:
        return {}

    return coordinates_by_name


# Google Places integration helpers
GOOGLE_PLACES_API_KEY = os.getenv('GOOGLE_PLACES_API_KEY', 'YOUR_GOOGLE_PLACES_API_KEY')
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# This function checks whether Google Places API is enabled

def google_places_enabled():
    key = (GOOGLE_PLACES_API_KEY or "").strip()
    return bool(key and key != "YOUR_GOOGLE_PLACES_API_KEY")

# This function normalizes city names for cleaner searching

def normalize_city_key(value):
    cleaned = normalize_place_name(value)
    for suffix in (" valley", " beach", " city", " district"):
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip()
    return cleaned

# This function finds a destination using its name

def get_destination_record_by_name(name):
    search_value = normalize_city_key(name)
    destinations = fetch_all_destinations()

    for destination in destinations:
        destination_name = destination.get("name", "")
        destination_key = normalize_city_key(destination_name)
        if destination_key == search_value or search_value in destination_key or destination_key in search_value:
            return destination

    return None

# This function creates multiple city search variations

def get_city_search_terms(city):
    requested_city = (city or "").strip()
    if not requested_city:
        return []

    terms = []
    candidate_values = [requested_city, normalize_city_key(requested_city)]
    
    # Try adding country code for Pakistan locations
    if requested_city and not any(c.isdigit() for c in requested_city):
        candidate_values.append(f"{requested_city}, Pakistan")
    
    destination = get_destination_record_by_name(requested_city)

    if destination:
        candidate_values.extend(
            [
                destination.get("name", ""),
                normalize_city_key(destination.get("name", "")),
                destination.get("region", ""),
            ]
        )

    for value in candidate_values:
        for variant in (str(value or "").strip(), normalize_city_key(value)):
            if not variant:
                continue
            lowered_variant = variant.lower()
            if lowered_variant not in [existing.lower() for existing in terms]:
                terms.append(variant)

    return terms

# This function fetches latitude and longitude of a city

def get_location_coordinates(city):
    destination = get_destination_record_by_name(city)
    if destination:
        latitude = destination.get("latitude")
        longitude = destination.get("longitude")
        if latitude is not None and longitude is not None:
            return float(latitude), float(longitude)

    coordinate_lookup = load_destination_coordinate_lookup()
    for search_term in get_city_search_terms(city):
        matched_coordinates = coordinate_lookup.get(normalize_place_name(search_term))
        if matched_coordinates:
            return matched_coordinates

    return None


# This function calls Google Places for live restaurants or attractions near a city.
def fetch_google_places(query, location, radius=5000, place_type='restaurant'):
    if not google_places_enabled() or not location:
        return []

    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        'key': GOOGLE_PLACES_API_KEY,
        'location': location,  # lat,lng
        'radius': radius,
        'type': place_type,
        'keyword': query
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get('status') == 'OK':
            return [
                {
                    'name': place['name'],
                    'rating': place.get('rating', 0),
                    'address': place.get('vicinity', ''),
                    'place_id': place['place_id'],
                    'city': query,
                    'type': place_type.replace("_", " ").title(),
                    'price': 0,
                    'source': 'google_places'
                } for place in data.get('results', [])
            ]
        return []
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return []


# This function combines database restaurants with Google results while removing duplicates.
def merge_restaurant_results(city, database_rows, google_rows):
    merged = []
    seen_keys = set()

    for row in database_rows:
        row_copy = dict(row)
        row_copy["source"] = row_copy.get("source") or "database"
        dedupe_key = normalize_place_name(row_copy.get("name"))
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        merged.append(row_copy)

    for row in google_rows:
        name = row.get("name")
        dedupe_key = normalize_place_name(name)
        if dedupe_key in seen_keys:
            continue

        seen_keys.add(dedupe_key)
        merged.append(
            {
                "id": None,
                "name": name,
                "city": city,
                "rating": float(row.get("rating") or 0),
                "type": row.get("type") or "Restaurant",
                "price": row.get("price") or 0,
                "address": row.get("address"),
                "place_id": row.get("place_id"),
                "source": row.get("source") or "google_places",
            }
        )

    return merged


# This function builds the restaurant list from local data first, then live Google data.
def fetch_restaurant_data(city):
    database_rows = fetch_restaurants_by_city(city)
    coordinates = get_location_coordinates(city)
    google_rows = []

    if coordinates:
        lat, lng = coordinates
        google_rows = fetch_google_places(city, f"{lat},{lng}")

    return merge_restaurant_results(city, database_rows, google_rows)


# This function returns safety advice from static city notes or generated destination details.
def build_advisory_response(city):
    city_key = normalize_city_key(city)
    advisory_data = STATIC_ADVISORIES.get(city_key)

    if advisory_data is None:
        for known_city, city_advisory in STATIC_ADVISORIES.items():
            if known_city in city_key or city_key in known_city:
                advisory_data = city_advisory
                break

    destination = get_destination_record_by_name(city)
    if advisory_data is not None:
        return {
            "city": city,
            "warning": advisory_data.get("warning"),
            "tips": advisory_data.get("tips", []),
            "source": "static_advisory",
            "destination": destination.get("name") if destination else city,
        }

    destination_name = destination.get("name") if destination else city
    best_season = destination.get("best_season") if destination else None
    typical_weather = destination.get("weather") if destination else None
    region = destination.get("region") if destination else None

    fallback_tips = [
        "Keep an offline copy of your hotel and transport details.",
        "Carry a charged phone and emergency cash.",
        "Check local weather shortly before departure.",
    ]

    if best_season:
        fallback_tips.insert(0, f"Best travel season for {destination_name} is {best_season}.")
    if typical_weather:
        fallback_tips.append(f"Typical conditions are usually {typical_weather.lower()}.")
    if region:
        fallback_tips.append(f"Review local transport conditions across {region}.")

    return {
        "city": city,
        "warning": f"Review local transport, weather and accommodation updates before visiting {destination_name}.",
        "tips": fallback_tips,
        "source": "generated_advisory",
        "destination": destination_name,
    }


# This function validates the Google sign-in token before trusting the user's email.
def verify_google_token(credential):
    if not credential:
        raise ValueError("Google credential is required")

    if not GOOGLE_CLIENT_ID:
        raise ValueError("Google login is not configured on the server")

    response = requests.get(
        "https://oauth2.googleapis.com/tokeninfo",
        params={"id_token": credential},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()

    if payload.get("aud") != GOOGLE_CLIENT_ID:
        raise ValueError("Google token audience does not match this application")

    email = payload.get("email")
    if not email:
        raise ValueError("Google account email was not provided")

    display_name = payload.get("name") or payload.get("given_name") or email.split("@")[0]
    return {"name": display_name, "email": email, "google_payload": payload}


# This function stores Google login details in the Flask session and formats the response.
def build_google_login_response(user_record, auth_source):
    session["user_id"] = user_record["user_id"]
    session["user_name"] = user_record["name"]
    session["user_email"] = user_record["email"]

    return {
        "message": "Google login successful",
        "user_id": user_record["user_id"],
        "name": user_record["name"],
        "email": user_record["email"],
        "auth_provider": "google",
        "auth_source": auth_source,
        "redirect_url": "/",
    }



# This API route returns live restaurant data if available, otherwise local restaurant data.
@app.route("/api/restaurants/<city>")
def api_restaurants(city):
    coordinates = get_location_coordinates(city)

    if coordinates:
        lat, lng = coordinates
        places = fetch_google_places(city, f"{lat},{lng}")

        if places:
            return jsonify(places)

    return jsonify(fetch_restaurants_by_city(city))


# This API route returns tourist attractions from Google Places for the selected city.
@app.route("/api/attractions/<city>")
def api_attractions(city):
    coordinates = get_location_coordinates(city)

    if coordinates:
        lat, lng = coordinates

        places = fetch_google_places(
            city,
            f"{lat},{lng}",
            place_type='tourist_attraction'
        )

        if places:
            return jsonify(places)

    return jsonify([])

# Near-me geolocation route
@app.route("/near-me", methods=["POST"])
def near_me():
    data = get_json_payload()
    lat = data.get("lat")
    lng = data.get("lng")
    if lat is None or lng is None:
        return jsonify({"error": "lat and lng required"}), 400

    try:
        user_lat = float(lat)
        user_lng = float(lng)
    except (TypeError, ValueError):
        return jsonify({"error": "lat and lng must be valid numbers"}), 400

    coordinate_lookup = load_destination_coordinate_lookup()

    # Find destinations within a 100km radius of the user's current location.
    destinations = fetch_all_destinations()
    nearby = []
    for destination in destinations:
        destination_lat = destination.get("latitude")
        destination_lng = destination.get("longitude")

        if destination_lat is None or destination_lng is None:
            matched_coords = coordinate_lookup.get(normalize_place_name(destination.get("name")))
            if matched_coords:
                destination_lat, destination_lng = matched_coords
        if destination_lat is None or destination_lng is None:
            continue

        try:
            distance_km = haversine_distance_km(user_lat, user_lng, float(destination_lat), float(destination_lng))
        except (TypeError, ValueError):
            continue

        if distance_km <= 100:
            destination_with_distance = dict(destination)
            destination_with_distance["distance"] = round(distance_km, 2)
            nearby.append(destination_with_distance)

    nearby.sort(key=lambda item: item["distance"])
    return jsonify(nearby[:5])
# End near-me geolocation route


# This function fetches restaurants from MySQL and falls back to built-in sample data.
def fetch_restaurants_by_city(city):
    ensure_feature_tables()
    cur = get_cursor()
    try:
        search_terms = get_city_search_terms(city) or [city]
        primary_term = search_terms[0]
        cur.execute(
            """
            SELECT id, name, city, rating, type, price
            FROM restaurants
            WHERE LOWER(city)=LOWER(%s)
               OR LOWER(%s) LIKE CONCAT('%%', LOWER(city), '%%')
               OR LOWER(city) LIKE CONCAT('%%', LOWER(%s), '%%')
            ORDER BY rating DESC, name ASC
            """,
            (primary_term, primary_term, primary_term),
        )
        rows = cur.fetchall()
        restaurants = [
            {
                "id": row[0],
                "name": row[1] or "Restaurant",
                "city": row[2] or primary_term,
                "rating": float(row[3]) if row[3] is not None else 0,
                "type": row[4] or "Restaurant",
                "price": row[5] or 0,
                "source": "database",
            }
            for row in rows
        ]
        if restaurants:
            return restaurants

        for term in search_terms:
            fallback = FALLBACK_RESTAURANTS.get(normalize_city_key(term))
            if fallback:
                return fallback
        return []
    finally:
        cur.close()


# This function fetches upcoming events from PredictHQ first, then the local database.
def fetch_events_by_city(city):
    import requests as req
    import datetime

    PREDICTHQ_KEY = os.getenv("PREDICTHQ_API_KEY", "").strip()

    # -------- Step 1: PredictHQ API --------
    # Live events are preferred when the optional API key is available.
    if PREDICTHQ_KEY:
        try:
            response = req.get(
                "https://api.predicthq.com/v1/events/",
                headers={
                    "Authorization": f"Bearer {PREDICTHQ_KEY}",
                    "Accept": "application/json"
                },
                params={
                    "q": city,
                    "country": "PK",
                    "limit": 6,
                    "sort": "start",
                    "active.gte": datetime.datetime.now().strftime(
                        "%Y-%m-%d"
                    )
                },
                timeout=8
            )

            if response.status_code == 200:
                data = response.json()
                phq_events = data.get("results", [])

                if phq_events:
                    results = []
                    for event in phq_events:
                        results.append({
                            "id": None,
                            "name": event.get("title", "Event"),
                            "city": city,
                            "event_date": event.get(
                                "start", "TBA"
                            )[:10],
                            "description": (
                                f"Category: "
                                f"{event.get('category', 'Event')}. "
                                f"Location: {city}, Pakistan."
                            ),
                            "url": "",
                            "image": "",
                            "is_upcoming": True,
                            "source": "predicthq"
                        })
                    return results

                print(
                    f"[EVENTS] PredictHQ: "
                    f"no results for '{city}', "
                    f"trying database..."
                )

        except Exception as e:
            print(f"[EVENTS] PredictHQ error: {e}")

    # -------- Step 2: Database --------
    # The local database keeps event results available for offline/demo use.
    ensure_feature_tables()
    cur = get_cursor()
    try:
        search_terms = get_city_search_terms(city) or [city]
        primary_term = search_terms[0]

        print(f"[EVENTS] DB search for: '{primary_term}'")

        cur.execute(
            """
            SELECT id, name, city, event_date, description
            FROM events
            WHERE (
                LOWER(city) = LOWER(%s)
                OR LOWER(%s) LIKE CONCAT('%%', LOWER(city), '%%')
                OR LOWER(city) LIKE CONCAT('%%', LOWER(%s), '%%')
            ) AND event_date >= CURDATE()
            ORDER BY event_date ASC
            """,
            (primary_term, primary_term, primary_term),
        )
        rows = cur.fetchall()
        print(f"[EVENTS] DB rows found: {len(rows)}")

        if not rows:
            cur.execute(
                """
                SELECT id, name, city, event_date, description
                FROM events
                WHERE (
                    LOWER(city) = LOWER(%s)
                    OR LOWER(%s) LIKE CONCAT('%%', LOWER(city), '%%')
                    OR LOWER(city) LIKE CONCAT('%%', LOWER(%s), '%%')
                )
                ORDER BY event_date DESC
                """,
                (primary_term, primary_term, primary_term),
            )
            rows = cur.fetchall()
            print(
                f"[EVENTS] DB rows (all dates): {len(rows)}"
            )

        return [
            {
                "id": row[0],
                "name": row[1] or "Event",
                "city": row[2] or primary_term,
                "event_date": (
                    row[3].isoformat() if row[3] else None
                ),
                "description": (
                    row[4] or "No description available."
                ),
                "is_upcoming": bool(row[3]),
                "source": "database"
            }
            for row in rows
        ]

    finally:
        cur.close()

# This function loads saved preference answers for a user.
def get_user_preferences(user_id):
    if not user_id:
        return {}

    cur = get_cursor()
    try:
        cur.execute(
            """
            SELECT budget_range, travel_style, duration
            FROM user_preferences
            WHERE user_id=%s
            """,
            (user_id,),
        )
        row = cur.fetchone()
    finally:
        cur.close()

    if not row:
        return {}

    travel_style = (row[1] or "").strip()
    normalized_preference = travel_style.lower() if travel_style else None

    return {
        "budget": row[0],
        "budget_range": row[0],
        "travel_style": travel_style,
        "preference": normalized_preference,
        "duration": row[2],
    }


# This function loads a user's previous destination ratings.
def get_user_ratings(user_id):
    if not user_id:
        return {}

    cur = get_cursor()
    try:
        cur.execute(
            """
            SELECT destination_id, rating
            FROM user_ratings
            WHERE user_id=%s
            """,
            (user_id,),
        )
        return {row[0]: row[1] for row in cur.fetchall()}
    finally:
        cur.close()


# Collaborative-filtering helper
def get_all_user_ratings():
    cur = get_cursor()
    try:
        cur.execute("SELECT user_id, destination_id, rating FROM user_ratings")
        rows = cur.fetchall()
        return [{"user_id": row[0], "destination_id": row[1], "rating": row[2]} for row in rows]
    finally:
        cur.close()
# End collaborative-filtering helper


# This function merges NLP-detected values with saved profile preferences.
def merge_preference_data(nlp_result, stored_preferences):
    entities = dict(nlp_result.get("entities", {}))

    if entities.get("budget") is None and stored_preferences.get("budget") is not None:
        entities["budget"] = stored_preferences["budget"]

    if entities.get("duration") is None and stored_preferences.get("duration") is not None:
        entities["duration"] = stored_preferences["duration"]

    if not entities.get("preference") and stored_preferences.get("preference"):
        entities["preference"] = stored_preferences["preference"]

    return {"intent": nlp_result.get("intent", "search"), "entities": entities}


# This function reuses an existing Google user or creates one on first login.
def get_or_create_google_user(name, email):
    cur = get_cursor()
    try:
        cur.execute("SELECT id, name, email FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        if user:
            return {"user_id": user[0], "name": user[1], "email": user[2]}

        placeholder_password = generate_password_hash("google_oauth_placeholder")
        cur.execute(
            """
            INSERT INTO users (name, email, password)
            VALUES (%s, %s, %s)
            """,
            (name, email, placeholder_password),
        )
        mysql.connection.commit()
        return {"user_id": cur.lastrowid, "name": name, "email": email}
    finally:
        cur.close()


# -------- Routes --------

# This route shows the home page
@app.route("/")
def home():
    # The map key is sent to the template only after checking whether it is configured.
    maps_key = (GOOGLE_MAPS_API_KEY or "").strip()
    maps_enabled = bool(maps_key and maps_key != "YOUR_GOOGLE_MAPS_API_KEY")
    return render_template(
        "index.html",
        google_maps_api_key=maps_key,
        maps_enabled=maps_enabled,
    )


# This route shows the login page and passes Google login settings to the template.
@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html", google_client_id=GOOGLE_CLIENT_ID, google_login_enabled=bool(GOOGLE_CLIENT_ID))


# This route shows the registration page template.
@app.route("/register", methods=["GET"])
def register_page():
    return render_template("register.html")


# This route shows the logged-in user's profile page.
@app.route("/profile")
def profile_page():
    return render_template("profile.html")
# -------- Admin Security Check --------
def admin_required():
    if not session.get("user_id"):
        return jsonify({"error": "Login required"}), 401
    if not session.get("is_admin"):
        return jsonify({"error": "Admin access only"}), 403
    return None


# This route opens the admin dashboard page.
@app.route("/admin")
def admin_page():
    if not session.get("user_id"):
        return render_template("error.html",
            error_title="Unauthorized",
            error_message="You must be logged in as an administrator to access this page.",
            error_code=401), 401
    if not session.get("is_admin"):
        return render_template("error.html",
            error_title="Access Denied",
            error_message="You do not have permission to view this page. Admin access only.",
            error_code=403), 403
    return render_template("admin.html")

# This route clears the user session on logout
@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})

# -------- Authentication Routes --------

# This route handles Google login
@app.route("/google-login", methods=["POST", "GET"])
def google_login():
    try:
        payload = get_json_payload()
        credential = payload.get("credential") or payload.get("id_token")

        # Prefer a real Google ID token when the frontend provides one.
        if credential:
            google_identity = verify_google_token(credential)
            user = get_or_create_google_user(google_identity["name"], google_identity["email"])
            return jsonify(build_google_login_response(user, "google_id_token"))

        email = (payload.get("email") or "").strip()
        name = (payload.get("name") or "Google User").strip()

        # Manual email fallback is helpful during local development and testing.
        if not email:
            return json_error("Google credential or email is required")

        if GOOGLE_CLIENT_ID:
            return json_error("Google credential is required for this application", 401)

        user = get_or_create_google_user(name, email)
        return jsonify(build_google_login_response(user, "development_fallback"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except requests.RequestException:
        return jsonify({"error": "Unable to verify Google login right now"}), 503
    except Exception as exc:
        mysql.connection.rollback()
        return jsonify({"error": str(exc)}), 500


# This route handles user registration
@app.route("/register", methods=["POST"])
def register():
    data = get_json_payload()

    # Required fields are checked before any database work is attempted.
    if not all(data.get(field) for field in ("name", "email", "password")):
        return json_error("name, email and password are required")

    cur = get_cursor()
    try:
        # Email must stay unique so users do not accidentally create duplicate accounts.
        cur.execute("SELECT id FROM users WHERE email=%s", (data["email"],))
        if cur.fetchone():
            return json_error("Email already exists")

        cur.execute(
            """
            INSERT INTO users (name, email, password)
            VALUES (%s, %s, %s)
            """,
            (data["name"], data["email"], generate_password_hash(data["password"])),
        )
        mysql.connection.commit()
        session["user_id"] = cur.lastrowid
        session["user_name"] = data["name"]
        session["user_email"] = data["email"]
        return jsonify({"message": "Registered Successfully", "user_id": cur.lastrowid})
    except Exception as exc:
        mysql.connection.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        cur.close()

# This route verifies user login credentials
@app.route("/login", methods=["POST"])
def login():
    data = get_json_payload()

    if not data.get("email") or not data.get("password"):
        return json_error("email and password are required")

    cur = get_cursor()
    try:
        cur.execute("SELECT id, name, email, password, is_admin FROM users WHERE email=%s", (data["email"],))
        user = cur.fetchone()
    finally:
        cur.close()

    if user and check_password_hash(user[3], data["password"]):
        session["user_id"] = user[0]
        session["user_name"] = user[1]
        session["user_email"] = user[2]
        session["is_admin"] = bool(user[4])   
        return jsonify({"message": "Login successful", "user_id": user[0], "name": user[1]})
    return jsonify({"error": "Invalid credentials"}), 401


# This route sends a personalized greeting to the user
@app.route("/greeting/<int:user_id>")
def greeting(user_id):
    cur = get_cursor()
    try:
        cur.execute("SELECT name FROM users WHERE id=%s", (user_id,))
        user = cur.fetchone()
    finally:
        cur.close()

    if user:
        return jsonify({"message": f"Welcome back, {user[0]}! Ready for your next adventure?"})

    return jsonify({"message": "Welcome Traveler!"})

# This route returns top recommended destinations
@app.route("/suggestions")
def suggestions():
    cur = get_cursor()
    try:
        cur.execute("""
            SELECT * FROM destinations
            ORDER BY id DESC
            LIMIT 5
        """)
        return jsonify([format_destination(row) for row in cur.fetchall()])
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        cur.close()

# This route returns trending travel destinations
@app.route("/trending")
def trending():
    return suggestions()

# This route returns frontend configuration settings
@app.route("/app-config")
def app_config():
    return jsonify(
        {
            "weather_enabled": weather_enabled(),
            "maps_enabled": True,
        }
    )

# This route returns nearby destinations of a region
@app.route("/near/<country>")
def near_destination(country):
    cur = get_cursor()
    try:
        cur.execute("""
            SELECT * FROM destinations
            WHERE region = %s
            ORDER BY id DESC
        """, (country,))
        return jsonify([format_destination(row) for row in cur.fetchall()])
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        cur.close()

# This route returns restaurants for a city
@app.route("/restaurants/<path:city>")
def restaurants(city):
    try:
        return jsonify(fetch_restaurant_data(city))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

# This route returns events for a city

@app.route("/events/<path:city>")
def events(city):
    try:
        return jsonify(fetch_events_by_city(city))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

# This route returns travel advisories and safety tips
@app.route("/advisory/<city>")
def get_advisory(city):
    # This route handles travel safety tips for a selected destination.
    # Static advisories keep the feature working even when the advisories table is empty.
    try:
        ensure_feature_tables()
        cur = get_cursor()
        try:
            cur.execute(
                """
                SELECT city, warning, tips
                FROM advisories
                WHERE LOWER(city)=LOWER(%s)
                """,
                (city,),
            )
            data = cur.fetchone()
        finally:
            cur.close()

        if data:
            tips = data[2]
            if isinstance(tips, str):
                tips = [tip.strip() for tip in tips.replace("\r", "\n").split("\n") if tip.strip()]
            return jsonify({"city": data[0], "warning": data[1], "tips": tips or [], "source": "database"})

        return jsonify(build_advisory_response(city))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# This route generates AI-based travel recommendations

@app.route("/recommend", methods=["POST"])
def recommend():

    data = get_json_payload()

    message = (data.get("message") or "").strip()

    user_id = data.get("user_id")

    if not message and not user_id:
        return json_error("message or user_id is required")

    try:

        # -------- NLP Processing --------
        nlp_result = process_query(message)
        nlp_result["message"] = message  # Store original message for nearby keyword detection

        # -------- User Preferences --------
        stored_preferences = get_user_preferences(user_id)

        merged_query = merge_preference_data(
            nlp_result,
            stored_preferences
        )
        merged_query["message"] = message  # Preserve message in merged query

        # -------- User Ratings --------
        user_ratings = get_user_ratings(user_id)

        # -------- Collaborative Filtering --------
        all_user_ratings = get_all_user_ratings()

        cf_matrix, user_to_idx, dest_to_idx = (
            build_user_item_matrix(all_user_ratings)
        )

        # -------- Destination Data --------
        destinations = fetch_all_destinations()

        # -------- Train ML Model --------
        df, similarity_matrix = train_model(destinations)

        # -------- AI Recommendations --------
        recommendations = get_recommendations(
            merged_query,
            df,
            similarity_matrix,
            user_ratings,
            cf_matrix=cf_matrix,
            user_to_idx=user_to_idx,
            dest_to_idx=dest_to_idx,
            user_id=user_id,
            destination_aliases_map=DESTINATION_SEARCH_ALIASES
        )

        if message:
            # Natural-language matches are blended in front so direct wording feels responsive.
            natural_matches = natural_language_destination_matches(message, destinations, limit=5)
            if natural_matches:
                merged_recommendations = []
                seen_ids = set()
                for destination in natural_matches + recommendations:
                    destination_id = destination.get("id")
                    if destination_id in seen_ids:
                        continue
                    seen_ids.add(destination_id)
                    merged_recommendations.append(destination)
                    if len(merged_recommendations) >= 5:
                        break
                recommendations = merged_recommendations

        
        # -------- Final Response --------
        return jsonify(
            {
                "nlp": merged_query,
                "recommendations": recommendations,
                "count": len(recommendations),
                "ai_engine": "active"
            }
        )

    except Exception as exc:

        return jsonify(
            {
                "error": str(exc)
            }
        ), 500

# This route performs AI-powered smart destination search
@app.route("/smart-search", methods=["POST"])
def smart_search():
    data = get_json_payload()
    query = (data.get("query") or "").strip()

    try:
        # Strict search is tried first so exact destination names stay predictable.
        strict_results = search_destinations(query)
        if strict_results:
            nlp_result = process_query(query)
            return jsonify(
                {
                    "intent": nlp_result.get("intent"),
                    "entities": nlp_result.get("entities"),
                    "results": strict_results,
                    "count": len(strict_results),
                    "source": "strict_search",
                }
            )

        nlp_result = process_query(query)
        entities = nlp_result.get("entities", {})
        has_ai_signal = any(
            entities.get(key) is not None
            for key in ("budget", "duration", "preference", "region", "destination")
        )

        # If the query has no recognizable travel meaning, return empty instead of guessing.
        if query and not has_ai_signal:
            return jsonify(
                {
                    "intent": nlp_result.get("intent"),
                    "entities": entities,
                    "results": [],
                    "count": 0,
                    "source": "strict_search",
                }
            )

        # When the query has travel intent, the recommender can provide broader matches.
        destinations = fetch_all_destinations()
        df, similarity_matrix = train_model(destinations)
        results = get_recommendations(nlp_result, df, similarity_matrix, {})

        return jsonify(
            {
                "intent": nlp_result.get("intent"),
                "entities": nlp_result.get("entities"),
                "results": results,
                "count": len(results),
                "source": "ai_search",
            }
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

# This route handles destination search requests from frontend

@app.route("/search-destinations", methods=["POST"])
def search_destinations_route():
    # This endpoint powers the normal search box with predictable filtering.
    data = get_json_payload()
    query = (data.get("query") or "").strip()

    try:
        results = search_destinations(query)
        return jsonify({"query": query, "results": results, "count": len(results)})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

# This route generates a travel itinerary plan
@app.route("/itinerary", methods=["POST"])
def itinerary():
    data = get_json_payload()

    try:
        days = int(data.get("days", 3))
        preference = (data.get("preference") or "general").strip().lower()
        destination_name = (data.get("destination_name") or "").strip()

        # A trip needs at least one day before an itinerary can be created.
        if days <= 0:
            return json_error("days must be greater than 0")

        plan = generate_itinerary(days, preference)
        return jsonify(
            {
                "plan": plan,
                "days": days,
                "preference": preference,
                "destination_name": destination_name or None,
                "count": len(plan),
            }
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

# This route saves user travel plans into the database
@app.route("/save-plan", methods=["POST"])
def save_plan():
    ensure_feature_tables()
    data = get_json_payload()

    # A saved plan must always belong to one user and one destination.
    if not all(data.get(field) not in (None, "") for field in ("user_id", "destination_id", "itinerary")):
        return json_error("user_id, destination_id and itinerary are required")

    cur = get_cursor()
    try:
        cur.execute(
            """
            INSERT INTO saved_plans (user_id, destination_id, itinerary)
            VALUES (%s, %s, %s)
            """,
            (
                data["user_id"],
                data["destination_id"],
                serialize_itinerary(data["itinerary"]),
            ),
        )
        mysql.connection.commit()
        return jsonify({"message": "Travel plan saved", "plan_id": cur.lastrowid})
    except Exception as exc:
        mysql.connection.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        cur.close()

# This route fetches all saved travel plans for a user
@app.route("/my-plans/<int:user_id>")
def my_plans(user_id):
    ensure_feature_tables()
    cur = get_cursor()
    try:
        cur.execute(
            """
            SELECT sp.id, sp.user_id, sp.destination_id, sp.itinerary, sp.created_at,
                   d.name, d.region, d.image
            FROM saved_plans sp
            LEFT JOIN destinations d ON d.id = sp.destination_id
            WHERE sp.user_id=%s
            ORDER BY sp.created_at DESC
            """,
            (user_id,),
        )
        rows = cur.fetchall()
        return jsonify(
            [
                {
                    "id": row[0],
                    "user_id": row[1],
                    "destination_id": row[2],
                    "itinerary": deserialize_itinerary(row[3]),
                    "created_at": row[4].isoformat() if row[4] else None,
                    "destination_name": row[5],
                    "destination_region": row[6],
                    "image": row[7],
                }
                for row in rows
            ]
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        cur.close()


# This route calculates estimated travel budget
@app.route("/calculate-budget", methods=["POST"])
def calculate_budget():
    data = get_json_payload()
    destination_id = data.get("destination_id")
    days = data.get("days")

    if destination_id is None or days is None:
        return json_error("destination_id and days are required")

    try:
        days = int(days)
    except (TypeError, ValueError):
        return json_error("days must be a valid integer")

    cur = get_cursor()
    try:
        cur.execute(
            """
            SELECT cost, hotel_cost_per_day, meal_cost_per_day, travel_cost
            FROM destinations
            WHERE id=%s
            """,
            (destination_id,),
        )
        row = cur.fetchone()
    finally:
        cur.close()

    if not row:
        return jsonify({"error": "Destination not found"}), 404

    hotel_cost = (row[1] or 0) * days
    meal_cost = (row[2] or 0) * days
    travel_cost = row[3] or 0
    destination_cost = row[0] or 0

    # The total combines per-day costs with one-time travel and destination costs.
    return jsonify(
        {
            "hotel": hotel_cost,
            "meals": meal_cost,
            "travel": travel_cost,
            "destination_cost": destination_cost,
            "total": hotel_cost + meal_cost + travel_cost + destination_cost,
        }
    )

# This route returns destinations under a specific budget
@app.route("/budget-under/<string:budget>")
def budget_under(budget):
    cur = get_cursor()
    try:
        cur.execute("""
            SELECT * FROM destinations
            WHERE budget_range = %s
            ORDER BY id DESC
        """, (budget,))
        return jsonify([format_destination(row) for row in cur.fetchall()])
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        cur.close()



# This route saves user travel preferences
@app.route("/save-preferences", methods=["POST"])
def save_preferences():
    data = get_json_payload()
    budget_range = data.get("budget_range") or data.get("budget")

    # Each field is checked separately so the frontend can show a clear missing-field message.
    if data.get("user_id") in (None, ""):
        return json_error("Missing field: user_id")
    if data.get("travel_style") in (None, ""):
        return json_error("Missing field: travel_style")
    if data.get("duration") in (None, ""):
        return json_error("Missing field: duration")
    if budget_range in (None, ""):
        return json_error("Missing field: budget_range")

    cur = get_cursor()
    try:
        # One preference row per user is kept fresh with an upsert.
        cur.execute(
            """
            INSERT INTO user_preferences (user_id, budget_range, travel_style, duration)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            budget_range=%s,
            travel_style=%s,
            duration=%s
            """,
            (
                data["user_id"],
                budget_range,
                data["travel_style"],
                data["duration"],
                budget_range,
                data["travel_style"],
                data["duration"],
            ),
        )
        mysql.connection.commit()
        return jsonify({"message": "Preferences Saved"})
    except Exception as exc:
        mysql.connection.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        cur.close()

# This route fetches saved user preferences
@app.route("/get-preferences/<int:user_id>")
def fetch_preferences(user_id):
    preferences = get_user_preferences(user_id)
    if not preferences:
        return jsonify({})

    return jsonify(
        {
            "travel_style": preferences.get("travel_style"),
            "preference": preferences.get("preference"),
            "budget": preferences.get("budget"),
            "budget_range": preferences.get("budget_range"),
            "duration": preferences.get("duration"),
        }
    )


# This route stores or updates a user's rating for a destination.
@app.route("/rate", methods=["POST"])
def rate():
    data = get_json_payload()

    if not all(data.get(field) is not None for field in ("user_id", "destination_id", "rating")):
        return json_error("user_id, destination_id and rating are required")

    cur = get_cursor()
    try:
        cur.execute(
            """
            INSERT INTO user_ratings (user_id, destination_id, rating)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE rating=%s
            """,
            (data["user_id"], data["destination_id"], data["rating"], data["rating"]),
        )
        mysql.connection.commit()
        return jsonify({"message": "Rating Saved"})
    except Exception as exc:
        mysql.connection.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        cur.close()


# This route stores feedback submitted by travelers.
@app.route("/submit-feedback", methods=["POST"])
def submit_feedback():
    # This route stores user feedback from the home page form.
    # Admin can review the same feedback from the dashboard.
    ensure_feature_tables()
    data = get_json_payload()

    required_fields = ("name", "email", "message")
    if not all((data.get(field) or "").strip() for field in required_fields):
        return json_error("name, email and message are required")

    cur = get_cursor()
    try:
        cur.execute(
            """
            INSERT INTO feedback (user_id, name, email, message, feedback)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                data.get("user_id"),
                data["name"].strip(),
                data["email"].strip(),
                data["message"].strip(),
                data["message"].strip(),
            ),
        )
        mysql.connection.commit()
        return jsonify({"message": "Feedback submitted successfully"})
    except Exception as exc:
        mysql.connection.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        cur.close()


# This route returns feedback messages for the admin dashboard.
@app.route("/admin/feedback")
def admin_feedback():
    err = admin_required()    
    if err: return err 
    # Admin feedback list is loaded asynchronously on the dashboard.
    ensure_feature_tables()
    cur = get_cursor()
    try:
        cur.execute(
            """
            SELECT id, user_id, name, email, COALESCE(message, feedback) AS feedback_text, created_at
            FROM feedback
            ORDER BY created_at DESC, id DESC
            """
        )
        rows = cur.fetchall()
        return jsonify(
            [
                {
                    "id": row[0],
                    "user_id": row[1],
                    "name": row[2],
                    "email": row[3],
                    "message": row[4],
                    "feedback": row[4],
                    "created_at": row[5].isoformat() if row[5] else None,
                }
                for row in rows
            ]
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        cur.close()




# -------- Admin Management Routes --------

# This route returns all destinations for admin management.
@app.route("/admin/destinations")
def admin_destinations():
    err = admin_required()    
    if err: return err
    try:
        return jsonify(fetch_all_destinations())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# This route returns all restaurants managed by admin.
@app.route("/admin/restaurants")
def admin_restaurants():
    try:
        ensure_feature_tables()
        cur = get_cursor()
        try:
            cur.execute(
                """
                SELECT id, name, city, rating, type, price
                FROM restaurants
                ORDER BY city ASC, rating DESC, name ASC
                """
            )
            rows = cur.fetchall()
            return jsonify(
                [
                    {
                        "id": row[0],
                        "name": row[1],
                        "city": row[2],
                        "rating": float(row[3]) if row[3] is not None else 0,
                        "type": row[4],
                        "price": row[5],
                    }
                    for row in rows
                ]
            )
        finally:
            cur.close()
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# This route adds a restaurant from the admin dashboard.
@app.route("/admin/restaurants", methods=["POST"])
def add_restaurant():
    ensure_feature_tables()
    data = get_json_payload()

    required_fields = ("name", "city", "rating", "type", "price")
    if not all(data.get(field) not in (None, "") for field in required_fields):
        return json_error("Missing required restaurant fields")

    cur = get_cursor()
    try:
        cur.execute(
            """
            INSERT INTO restaurants (name, city, rating, type, price)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                data["name"],
                data["city"],
                data["rating"],
                data["type"],
                data["price"],
            ),
        )
        mysql.connection.commit()
        return jsonify({"message": "Restaurant added successfully", "restaurant_id": cur.lastrowid})
    except Exception as exc:
        mysql.connection.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        cur.close()


# This route deletes a restaurant from the admin dashboard.
@app.route("/admin/restaurants/<int:restaurant_id>", methods=["DELETE"])
def delete_restaurant(restaurant_id):
    ensure_feature_tables()
    cur = get_cursor()
    try:
        cur.execute("DELETE FROM restaurants WHERE id=%s", (restaurant_id,))
        mysql.connection.commit()
        return jsonify({"message": "Restaurant deleted"})
    except Exception as exc:
        mysql.connection.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        cur.close()


# This route returns all events managed by admin.
@app.route("/admin/events")
def admin_events():
    try:
        ensure_feature_tables()
        cur = get_cursor()
        try:
            cur.execute(
                """
                SELECT id, name, city, event_date, description
                FROM events
                ORDER BY event_date ASC, city ASC, name ASC
                """
            )
            rows = cur.fetchall()
            return jsonify(
                [
                    {
                        "id": row[0],
                        "name": row[1],
                        "city": row[2],
                        "event_date": row[3].isoformat() if row[3] else None,
                        "description": row[4],
                    }
                    for row in rows
                ]
            )
        finally:
            cur.close()
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# This route adds an event from the admin dashboard.
@app.route("/admin/events", methods=["POST"])
def add_event():
    ensure_feature_tables()
    data = get_json_payload()

    required_fields = ("name", "city", "event_date", "description")
    if not all(data.get(field) not in (None, "") for field in required_fields):
        return json_error("Missing required event fields")

    cur = get_cursor()
    try:
        cur.execute(
            """
            INSERT INTO events (name, city, event_date, description)
            VALUES (%s, %s, %s, %s)
            """,
            (
                data["name"],
                data["city"],
                data["event_date"],
                data["description"],
            ),
        )
        mysql.connection.commit()
        return jsonify({"message": "Event added successfully", "event_id": cur.lastrowid})
    except Exception as exc:
        mysql.connection.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        cur.close()


# This route deletes an event from the admin dashboard.
@app.route("/admin/events/<int:event_id>", methods=["DELETE"])
def delete_event(event_id):
    ensure_feature_tables()
    cur = get_cursor()
    try:
        cur.execute("DELETE FROM events WHERE id=%s", (event_id,))
        mysql.connection.commit()
        return jsonify({"message": "Event deleted"})
    except Exception as exc:
        mysql.connection.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        cur.close()

# This route adds a new destination from admin panel
@app.route("/admin/add", methods=["POST"])
def add_destination():
    data = get_json_payload()

    required_fields = ("name", "type", "region", "cost", "weather", "best_season")
    if not all(data.get(field) not in (None, "") for field in required_fields):
        return json_error("Missing required destination fields")

    cur = get_cursor()
    try:
        cur.execute(
            """
            INSERT INTO destinations
            (name, type, region, cost, weather, best_season, activities, safety_rating,
             user_rating, image, hotel_cost_per_day, meal_cost_per_day, travel_cost)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                data.get("name"),
                data.get("type"),
                data.get("region"),
                data.get("cost"),
                data.get("weather"),
                data.get("best_season"),
                data.get("activities", ""),
                data.get("safety_rating", 0),
                data.get("user_rating", 0),
                data.get("image", ""),
                data.get("hotel_cost_per_day", 0),
                data.get("meal_cost_per_day", 0),
                data.get("travel_cost", 0),
            ),
        )
        mysql.connection.commit()
        return jsonify({"message": "Destination Added Successfully", "destination_id": cur.lastrowid})
    except Exception as exc:
        mysql.connection.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        cur.close()

# This route deletes a destination from admin panel
@app.route("/admin/delete/<int:destination_id>", methods=["DELETE"])
def admin_delete(destination_id):
    err = admin_required()    
    if err: return err
    cur = get_cursor()
    try:
        cur.execute("DELETE FROM destinations WHERE id=%s", (destination_id,))
        mysql.connection.commit()
        return jsonify({"message": "Deleted"})
    except Exception as exc:
        mysql.connection.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        cur.close()


# This route updates core destination details from the admin panel.
@app.route("/admin/update/<int:destination_id>", methods=["PUT"])
def admin_update(destination_id):
    err = admin_required()    
    if err: return err
    data = get_json_payload()

    cur = get_cursor()
    try:
        cur.execute(
            """
            UPDATE destinations
            SET cost=%s, weather=%s, best_season=%s
            WHERE id=%s
            """,
            (data["cost"], data["weather"], data["best_season"], destination_id),
        )
        mysql.connection.commit()
        return jsonify({"message": "Updated"})
    except Exception as exc:
        mysql.connection.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        cur.close()


# This route adds a model name that can be activated later from admin tools.
@app.route("/admin/add-model", methods=["POST"])
def add_model():
    err = admin_required()    
    if err: return err
    data = get_json_payload()
    model_name = (data.get("model_name") or "").strip()

    if not model_name:
        return json_error("Model name required")

    cur = get_cursor()
    try:
        cur.execute("SELECT id, status FROM ai_models WHERE model_name=%s", (model_name,))
        existing_model = cur.fetchone()
        if existing_model:
            return jsonify(
                {
                    "message": "Model already exists",
                    "model_id": existing_model[0],
                    "status": existing_model[1],
                }
            )

        cur.execute(
            """
            INSERT INTO ai_models (model_name, status)
            VALUES (%s, 'inactive')
            """,
            (model_name,),
        )
        mysql.connection.commit()
        return jsonify({"message": "Model Added Successfully", "model_id": cur.lastrowid})
    except Exception as exc:
        mysql.connection.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        cur.close()


# This helper marks one AI model active and turns the others inactive.
def activate_model_by_id(model_id):
    cur = get_cursor()
    try:
        cur.execute("UPDATE ai_models SET status='inactive'")
        cur.execute("UPDATE ai_models SET status='active' WHERE id=%s", (model_id,))
        mysql.connection.commit()
        return True
    finally:
        cur.close()


# This route activates an AI model from either JSON payload or URL parameter.
@app.route("/admin/activate-model", methods=["POST"])
@app.route("/admin/activate-model/<int:model_id>", methods=["PUT", "POST"])
def activate_model(model_id=None):
    err = admin_required()    
    if err: return err
    try:
        if model_id is None:
            data = get_json_payload()
            model_id = data.get("model_id")

        if not model_id:
            return json_error("model_id is required")

        activate_model_by_id(model_id)
        return jsonify({"message": "Model Activated"})
    except Exception as exc:
        mysql.connection.rollback()
        return jsonify({"error": str(exc)}), 500

# This route returns all available AI models
@app.route("/admin/models")
def get_models():
    err = admin_required()    
    if err: return err 
    cur = get_cursor()
    try:
        cur.execute("SELECT id, model_name, status FROM ai_models ORDER BY id DESC")
        rows = cur.fetchall()
        return jsonify([{"id": row[0], "name": row[1], "status": row[2]} for row in rows])
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        cur.close()

# This route refreshes the recommendation dataset
@app.route("/admin/refresh-dataset")
def refresh_dataset():
    err = admin_required()    
    if err: return err 
    try:
        destinations = fetch_all_destinations()
        train_model(destinations)
        return jsonify({"message": "Recommendation dataset refreshed successfully"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

# This route returns user activity statistics for admin dashboard
@app.route("/admin/user-activity")
def user_activity():
    err = admin_required()    
    if err: return err 
    ensure_feature_tables()
    cur = get_cursor()
    try:
        # These counts feed the summary cards on the admin dashboard.
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM user_ratings")
        total_ratings = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM feedback")
        total_feedback = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM ai_models")
        total_models = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM restaurants")
        total_restaurants = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM events")
        total_events = cur.fetchone()[0]

        return jsonify(
            {
                "total_users": total_users,
                "total_ratings": total_ratings,
                "total_feedback": total_feedback,
                "total_models": total_models,
                "total_restaurants": total_restaurants,
                "total_events": total_events,
            }
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        cur.close()

  # This starts the Flask application in debug mode    
if __name__ == "__main__":
    app.run(debug=True)
