import os
from flask import Flask, jsonify, request, session, redirect, url_for
import requests
from datetime import datetime
import random

# ========== CONFIG ==========
SECRET_KEY = os.environ.get("FLASK_SECRET", "change_this_secret_in_prod")
app = Flask(__name__)
app.secret_key = SECRET_KEY

# ⭐ FIX UNICODE ISSUE
app.config['JSON_AS_ASCII'] = False


# Offline quotes (local fallback)
OFFLINE_QUOTES = [
    "Whoever does not show mercy to others will not be shown mercy. — Prophet Muhammad (pbuh)",
    "The best among you are those who have the best manners and character.",
    "Read! In the name of your Lord who created. — Quran 96:1"
]

# ======= HELPERS ========


def fetch_json(url, params=None, headers=None, timeout=8):
    try:
        r = requests.get(url, params=params, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# ========== ENDPOINTS ==========


@app.route("/")
def home():
    return "Assalamu Alaikum — Muslim API running. Use /docs for endpoints."


@app.route("/docs")
def docs():
    return jsonify({
        "endpoints": {
            "/prayer?city=&country=": "Prayer times (AlAdhan API). Provide city & country or use lat/lon.",
            "/prayer_by_coords?lat=&lon=": "Prayer times by coordinates",
            "/quran/surah/<id>": "Get full surah text & audio (alquran.cloud)",
            "/quran/ayah/<surah>/<ayah>": "Single ayah",
            "/quran/list_surahs": "List surahs",
            "/audio?surah=&edition=": "Audio recitation (surah-level audio metadata)",
            "/hadith/collection/<collection>/<book>/<hadith_number>": "Hadith from Sunnah.com API (requires SUNNAH_API_KEY)",
            "/hadith/example": "Example hadith route demonstrating usage",
            "/quotes": "Offline Islamic quotes (random)",
            "/tasbih/count": "Get current session tasbih count",
            "/tasbih/increment": "Increment session tasbih by 1 (or use /tasbih?count=33)",
            "/tasbih/reset": "Reset counter",
            "/ui": "Optional small HTML UI"
        }
    })

# -------- Prayer times (AlAdhan) ----------


@app.route("/prayer")
def prayer_by_city():
    city = request.args.get("city")
    country = request.args.get("country")
    if city and country:
        url = "http://api.aladhan.com/v1/timingsByCity"
        params = {"city": city, "country": country, "method": 2}
        return fetch_json(url, params=params)
    return jsonify({"error": "Provide city and country parameters, e.g. /prayer?city=Karachi&country=Pakistan"})


@app.route("/prayer_by_coords")
def prayer_by_coords():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    if lat and lon:
        url = "http://api.aladhan.com/v1/timings"
        params = {"latitude": lat, "longitude": lon, "method": 2}
        return fetch_json(url, params=params)
    return jsonify({"error": "Provide lat and lon, e.g. /prayer_by_coords?lat=24.86&lon=67.01"})

# -------- Quran endpoints (alquran.cloud) ----------


@app.route("/quran/surah/<int:surah_id>")
def get_surah(surah_id):
    url = f"https://api.alquran.cloud/v1/surah/{surah_id}"
    return fetch_json(url)

# alias: /surah/<id> (friendly)


@app.route("/surah/<int:surah_id>")
def surah_alias(surah_id):
    return get_surah(surah_id)


@app.route("/quran/ayah/<int:surah_id>/<int:ayah_id>")
def get_ayah(surah_id, ayah_id):
    url = f"https://api.alquran.cloud/v1/ayah/{surah_id}:{ayah_id}"
    return fetch_json(url)


@app.route("/quran/list_surahs")
def list_surahs():
    url = "https://api.alquran.cloud/v1/surah"
    return fetch_json(url)

# Audio endpoint: returns audio metadata/links for a whole surah if available


@app.route("/audio")
def audio_surah():
    surah = request.args.get("surah")
    edition = request.args.get("edition", "ar.alafasy")  # default reciter
    if not surah:
        return jsonify({"error": "Provide surah number, e.g. /audio?surah=1 or /audio?surah=2&edition=ar.alafasy"})
    # alquran.cloud supports surah endpoints with edition; this often contains ayah audio links
    url = f"https://api.alquran.cloud/v1/surah/{surah}/{edition}"
    return fetch_json(url)

# -------- Hadith endpoints (Sunnah.com) ----------


@app.route("/hadith/collection/<collection>/<int:book>/<int:hadith_number>")
def get_hadith(collection, book, hadith_number):
    url = f"https://api.sunnah.com/v1/collections/{collection}/books/{book}/hadiths/{hadith_number}"
    api_key = os.environ.get("SUNNAH_API_KEY")
    if not api_key:
        return jsonify({
            "error": "Sunnah.com API requires an API key. Set SUNNAH_API_KEY env var to use this endpoint.",
            "note": "You can still use local hadith sources or other public hadith APIs."
        })
    headers = {"X-API-Key": api_key}
    return fetch_json(url, headers=headers)

# Friendly example route that shows how to request a famous hadith (this still needs API key)


@app.route("/hadith/example")
def hadith_example():
    return jsonify({
        "example": "GET /hadith/collection/bukhari/1/1",
        "note": "Replace 'bukhari','1','1' with collection/book/hadith_number. SUNNAH_API_KEY required for real data."
    })

# -------- Offline quotes ----------


@app.route("/quotes")
def quotes():
    return jsonify({"quote": random.choice(OFFLINE_QUOTES)})

# friendly alias


@app.route("/quote")
def quote_alias():
    return quotes()

# -------- Tasbih counter (session based) ----------


@app.route("/tasbih/count")
def tasbih_count():
    return jsonify({"count": session.get("tasbih_count", 0)})

# increment by 1 by default OR pass ?count=33 to add multiple


@app.route("/tasbih", methods=["GET", "POST"])
def tasbih():
    # GET will increment by 1 unless count provided as query param
    if request.method == "POST":
        # allow JSON body like {"count": 33}
        data = request.get_json(silent=True) or {}
        count_add = int(data.get("count", request.args.get("count", 1)))
    else:
        count_add = int(request.args.get("count", 1))
    current = session.get("tasbih_count", 0)
    current += max(0, count_add)
    session["tasbih_count"] = current
    return jsonify({"count": current})


@app.route("/tasbih/increment", methods=["GET", "POST"])
def tasbih_increment():
    # backward-compatible endpoint: increments by 1 or by count param
    count_add = int(request.args.get("count", 1))
    current = session.get("tasbih_count", 0) + max(0, count_add)
    session["tasbih_count"] = current
    return jsonify({"count": current})


@app.route("/tasbih/reset", methods=["POST", "GET"])
def tasbih_reset():
    session["tasbih_count"] = 0
    return jsonify({"count": 0})

# ======= Optional simple HTML UI (kept small) =======


@app.route("/ui")
def ui():
    html = """
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8"/>
        <title>Muslim Helper</title>
        <style>
          body{font-family:system-ui,Segoe UI,Roboto,Arial;padding:24px;background:#f6fbf6;color:#0b3d0b}
          .card{background:white;padding:18px;border-radius:12px;box-shadow:0 6px 18px rgba(10,10,10,0.06);max-width:760px;margin:12px auto}
          a.button{display:inline-block;padding:8px 12px;border-radius:8px;background:#0b6623;color:white;text-decoration:none;margin:6px 4px}
        </style>
      </head>
      <body>
        <div class="card">
          <h1>Assalamu Alaikum</h1>
          <p>Quick links for your Muslim helper API</p>
          <a class="button" href="/surah/1">Surah Al-Fatiha (API)</a>
          <a class="button" href="/prayer?city=Karachi&country=Pakistan">Prayer Times (Karachi)</a>
          <a class="button" href="/quotes">Quote</a>
          <a class="button" href="/tasbih/count">Tasbih Count</a>
        </div>
      </body>
    </html>
    """
    return html


# ======= Run server =======
if __name__ == "__main__":
    app.run(debug=True)
