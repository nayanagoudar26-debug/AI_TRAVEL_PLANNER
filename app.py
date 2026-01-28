from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types
import os
import json
from dotenv import load_dotenv
import requests
from concurrent.futures import ThreadPoolExecutor

# -------------------- ENV SETUP --------------------
load_dotenv()
GENAI_API_KEY = os.getenv("GENAI_API_KEY")

app = Flask(__name__)

# -------------------- GEMINI CLIENT --------------------
client = None
if GENAI_API_KEY:
    try:
        client = genai.Client(api_key=GENAI_API_KEY)
        print("Gemini client initialized successfully")
    except Exception as e:
        print("Gemini initialization failed:", e)
else:
    print("GENAI_API_KEY not found")

# -------------------- WIKI IMAGE --------------------
def get_wiki_image(query, city=None):
    try:
        search_url = "https://en.wikipedia.org/w/api.php"
        headers = {"User-Agent": "AI-Travel-Planner/1.0"}
        search_query = f"{query} {city}" if city else query

        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": search_query,
            "srlimit": 1
        }

        r = requests.get(search_url, params=params, headers=headers)
        data = r.json()
        results = data.get("query", {}).get("search", [])

        if not results:
            return None

        page_id = results[0]["pageid"]

        img_params = {
            "action": "query",
            "format": "json",
            "prop": "pageimages",
            "pageids": page_id,
            "pithumbsize": 600
        }

        img = requests.get(search_url, params=img_params, headers=headers).json()
        page = img["query"]["pages"].get(str(page_id))

        if page and "thumbnail" in page:
            return page["thumbnail"]["source"]

    except Exception as e:
        print("Wiki error:", e)

    return None

# -------------------- AI GENERATION --------------------
def get_gemini_recommendations(destination, days, budget, interests, travelers):
    if not client:
        return None

    prompt = f"""
    Act as an expert AI Travel Planner.

    Create a {days}-day trip itinerary for {destination}
    for {travelers} with a {budget} budget.
    Interests: {interests}

    Return STRICT JSON with:
    hotels, itinerary (day-wise), food.
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7
            )
        )

        if response and response.text:
            return json.loads(response.text)

    except Exception as e:
        print("AI ERROR:", e)

    return None

# -------------------- ROUTES --------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/plan", methods=["POST"])
def plan():
    if not client:
        return render_template("planner.html", error="Gemini API Key missing")

    destination = request.form.get("destination")
    days = request.form.get("days")
    budget = request.form.get("budget")

    interests = ", ".join(request.form.getlist("interests")) or "General"
    travelers_type = request.form.get("travelers_type")
    travelers_count = request.form.get("travelers_count")

    if travelers_type == "Solo":
        travelers = "Solo Traveler"
    elif travelers_type == "Couple":
        travelers = "Couple"
    else:
        travelers = f"{travelers_type} group of {travelers_count}"

    data = get_gemini_recommendations(
        destination, days, budget, interests, travelers
    )

    if not data:
        return render_template(
            "planner.html",
            error="Failed to generate itinerary. Try again."
        )

    # Attach images
    tasks = []
    for hotel in data.get("hotels", []):
        tasks.append((hotel, "hotel"))
    for day in data.get("itinerary", []):
        for place in day.get("places", []):
            tasks.append((place, "place"))
    for food in data.get("food", []):
        tasks.append((food, "food"))

    def fetch(task):
        item, category = task
        img = get_wiki_image(item.get("name"), destination)
        item["image"] = img or f"https://loremflickr.com/600/400/{category}"
        return item

    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(fetch, tasks)

    return render_template(
        "planner.html",
        data=data,
        destination=destination
    )

# -------------------- MAIN --------------------
if __name__ == "__main__":
    app.run(debug=True)
