"""Flask backend server for the Greenlight Simulator web application."""
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from flask import Flask, jsonify, request, send_from_directory
import joblib
import pandas as pd
from movie_lib import CLASS_NAMES, DATA_DIR, make_row

PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")

# Load model artifact
MODEL_PATH = BACKEND_DIR / "model.joblib"
print(f"Loading model artifact from {MODEL_PATH}...")
artifact = joblib.load(MODEL_PATH)
model = artifact["model"]
genres = artifact["genres"]
hist = artifact["hist"]
directors = artifact["directors"][:1500]
actors = artifact["actors"][:3000]
companies = artifact["companies"][:800]
print("Model loaded successfully.")

# Read OMDB API key
def get_omdb_key():
    if os.environ.get("OMDB_API_KEY"):
        return os.environ["OMDB_API_KEY"]
    for env_path in [PROJECT_ROOT / ".env", BACKEND_DIR / ".env"]:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.strip().startswith("OMDB_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return None

MONTH_NAMES_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_NAMES_FULL = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/static/<path:path>")
def serve_legacy_static(path):
    return send_from_directory(FRONTEND_DIR, path)

@app.route("/<path:path>")
def serve_frontend_assets(path):
    file_path = FRONTEND_DIR / path
    if file_path.exists():
        return send_from_directory(FRONTEND_DIR, path)
    return jsonify({"error": "Not found"}), 404

@app.route("/api/options", methods=["GET"])
def get_options():
    return jsonify({
        "genres": genres,
        "directors": directors,
        "actors": actors,
        "companies": companies,
        "months": [{"value": i + 1, "name": name} for i, name in enumerate(MONTH_NAMES_FULL)]
    })

@app.route("/api/predict", methods=["POST"])
def predict():
    data = request.get_json() or {}
    
    budget = float(data.get("budget", 40_000_000))
    runtime = float(data.get("runtime", 110))
    year = int(data.get("year", 2024))
    release_location = str(data.get("release_location", "Global release"))
    month = int(data.get("month", 6))
    picked_genres = list(data.get("genres", ["Action"]))
    english = bool(data.get("english", True))
    sequel = bool(data.get("sequel", False))
    director = data.get("director")
    if director == "(unknown / new director)" or not director:
        director = None
    cast = list(data.get("cast", []))[:3]
    company = data.get("company")
    companies_list = [company] if company and company != "(unknown)" else []

    # Map typed year within stable historical tree boundaries for feature row
    model_year = min(max(year, 1990), 2017)

    inp = {
        "budget": budget,
        "runtime": runtime,
        "year": model_year,
        "month": month,
        "genres": picked_genres,
        "english": english,
        "sequel": sequel,
        "cast": cast,
        "director": director,
        "companies": companies_list
    }

    # Model inference
    row = make_row(inp, genres, hist)
    proba = model.predict_proba(row)[0]
    most_likely_idx = int(proba.argmax())
    
    # Seasonality curve (chances across all 12 months)
    seasonality = []
    for m in range(1, 13):
        m_row = make_row({**inp, "month": m}, genres, hist)
        m_prob = model.predict_proba(m_row)[0]
        seasonality.append({
            "month": m,
            "month_name": MONTH_NAMES_SHORT[m - 1],
            "hit_prob": round(float(m_prob[2]) * 100, 1),
            "modest_prob": round(float(m_prob[1]) * 100, 1),
            "flop_prob": round(float(m_prob[0]) * 100, 1)
        })

    return jsonify({
        "most_likely": CLASS_NAMES[most_likely_idx],
        "most_likely_index": most_likely_idx,
        "probabilities": {
            CLASS_NAMES[0]: round(float(proba[0]) * 100, 1),
            CLASS_NAMES[1]: round(float(proba[1]) * 100, 1),
            CLASS_NAMES[2]: round(float(proba[2]) * 100, 1)
        },
        "seasonality": seasonality
    })

@app.route("/api/statistics", methods=["GET"])
def get_statistics():
    stats_file = DATA_DIR / "statistics.json"
    if not stats_file.exists():
        # Fallback if compute_stats has not finished yet
        return jsonify({"error": "Statistics not generated yet"}), 503
    with open(stats_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)

@app.route("/api/omdb", methods=["GET"])
def lookup_omdb():
    title = request.args.get("title", "").strip()
    year = request.args.get("year", "").strip()
    if not title:
        return jsonify({"Response": "False", "Error": "Title parameter is required."}), 400

    api_key = get_omdb_key()
    if not api_key:
        return jsonify({"Response": "False", "Error": "OMDB_API_KEY is not configured in .env."}), 400

    params = {"t": title, "apikey": api_key}
    if year:
        params["y"] = year
    
    try:
        url = "http://www.omdbapi.com/?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "GreenlightSimulator/1.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            result = json.loads(response.read().decode("utf-8"))
            return jsonify(result)
    except Exception as e:
        return jsonify({"Response": "False", "Error": str(e)}), 500

if __name__ == "__main__":
    print("Starting Greenlight Simulator server on http://localhost:5000 ...")
    app.run(host="127.0.0.1", port=5000, debug=False)

