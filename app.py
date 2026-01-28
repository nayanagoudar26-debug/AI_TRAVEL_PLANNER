from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types
import os
import json
from dotenv import load_dotenv
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load environment variables
import pathlib
env_path = pathlib.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)

# Fetch API Key from environment variables
GENAI_API_KEY = os.getenv("GENAI_API_KEY")

if GENAI_API_KEY:
    try:
        client = genai.Client(api_key=GENAI_API_KEY)
        print("Gemini client initialized")
    except Exception as e:
        print("Gemini initialization failed:", e)
else:
    print("GENAI_API_KEY not found. Running app without AI.")
    client = None


# Initialize client
if GENAI_API_KEY:
    print(f"DEBUG: Initializing Gemini Client with key: {GENAI_API_KEY[:5]}...{GENAI_API_KEY[-5:]}")
    client = genai.Client(api_key=GENAI_API_KEY)
else:
    print("DEBUG: No API Key available for client initialization.")
    client = None

@app.route('/status')
def api_status():
    if not client:
        return jsonify({"status": "error", "message": "API Client not initialized. Check .env file."})
    try:
        # Quick ping to verify connection
        client.models.generate_content(model="gemini-2.5-flash", contents="ping")
        return jsonify({"status": "connected", "message": "API is working perfectly!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

def get_wiki_image(query, city=None):
    """Fetches the main image for a query from Wikipedia with improved precision."""
    try:
        search_url = "https://en.wikipedia.org/w/api.php"
        headers = { "User-Agent": "TravelPlannerApp/1.0" }
        
        # If city is provided, ensure it's in the search to avoid irrelevant results
        search_query = f"{query} {city}" if city and city.lower() not in query.lower() else query
        
        params = {
            "action": "query", "format": "json", "list": "search",
            "srsearch": search_query, "srlimit": 3 # Get top 3 to find best match
        }
        r = requests.get(search_url, params=params, headers=headers)
        data = r.json()
        
        search_results = data.get("query", {}).get("search", [])
        if not search_results:
            return None
            
        # Try to find the best page ID from top results that isn't a disambiguation
        page_id = None
        for res in search_results:
            title = res["title"].lower()
            snippet = res.get("snippet", "").lower()
            
            query_words = set(query.lower().split())
            query_words.discard("hotel")
            query_words.discard("restaurant")
            query_words.discard("stay")
            
            title_relevance = any(word in title for word in query_words)
            city_relevance = city.lower() in title or city.lower() in snippet if city else True
            
            if not title_relevance and not city_relevance:
                continue 
                
            page_id = res["pageid"]
            
            img_url = "https://en.wikipedia.org/w/api.php"
            img_params = {
                "action": "query", "format": "json", "prop": "pageimages",
                "pageids": page_id, "pithumbsize": 600
            }
            r_img = requests.get(img_url, params=img_params, headers=headers)
            img_data = r_img.json()
            
            pages = img_data.get("query", {}).get("pages", {})
            page = pages.get(str(page_id))
            
            if page and "thumbnail" in page:
                 return page['thumbnail']['source']
                 
    except Exception as e:
        print(f"Wiki Image Error: {e}")
    return None

def get_gemini_recommendations(destination, days, budget, interests, travelers):
    if not client:
        return None
    
    prompt = f"""
    Act as an expert AI Travel Planner. 
    1. First, VALIDATE the destination: {destination}. Ensure you are planning for the correct country/region.
    2. Create a detailed {days}-day trip itinerary for {destination} for {travelers} people with a {budget} budget. Interests: {interests}.
    
    CRITICAL INSTRUCTION: 
    - You MUST generate itinerary items for EXACTLY {days} days.
    - Every place, hotel, and restaurant MUST include a numerical rating (1.0 to 5.0).
    - Every itinerary place MUST specify a "time" (e.g., "10:00 AM" or "Morning").
    
    Return STRICT JSON data with the following structure:
    {{
      "hotels": [
        {{ "name": "Hotel Name", "address": "Full Address with Country", "rating": "4.5", "price_range": "₹4000/night", "description": "Short catchy desc" }}
      ],
      "itinerary": [
        {{ 
           "day": 1, 
           "places": [
             {{ "name": "Place Name", "description": "Engaging description", "address": "Full Address", "rating": "4.7", "time": "10:00 AM" }}
           ] 
        }}
      ],
      "food": [
        {{ "name": "Restaurant Name", "type": "Cuisine Type", "rating": "4.8", "location": "Short address/area" }}
      ]
    }}
    
    Ensure:
    - At least 4 hotel options with prices in INR (₹).
    - Itinerary MUST have {days} distinct entries (Day 1 to Day {days}).
    - Each place MUST have a real address.
    - At least 4 food recommendations with ratings.
    """

    try:
        print(f"DEBUG: Generating for {destination}...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7
            )
        )
        
        if not response or not response.text:
            print(f"DEBUG ERROR: Empty response. Safety filters might be triggered.")
            return None
            
        print("DEBUG: Raw JSON received successfully.")
        return json.loads(response.text)
            
    except Exception as e:
        print(f"DEBUG CRITICAL AI ERROR: {str(e)}")
        # Log to file for route to read
        with open("generation_error.log", "w") as f:
            f.write(str(e))
        return None

@app.route("/plan", methods=["POST"])
def plan():
    try:
        # get user inputs (keep your existing code)
        destination = request.form.get("destination")
        days = request.form.get("days")
        budget = request.form.get("budget")
        interests = request.form.get("interests")

        if not client:
            return jsonify({
                "itinerary": "Demo Mode: AI service unavailable.",
                "days": [
                    {"day": 1, "plan": "Sample sightseeing and leisure activities."},
                    {"day": 2, "plan": "Local exploration and food experience."}
                ]
            })

        # YOUR EXISTING AI CODE HERE
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"Create a {days}-day itinerary for {destination}"
        )

        return jsonify(response.text)

    except Exception as e:
        print("Error during itinerary generation:", e)
        return jsonify({
            "itinerary": "Temporary error. Please try again later.",
            "error": str(e)
        })


        chat_prompt = f"""
        You are a helpful travel assistant for a trip to {context.get('destination', 'the destination')}.
        User currently seeing an itinerary for {context.get('days')} days.
        User asks: "{user_message}"
        
        Provide a helpful, short answer (max 3 sentences) suitable for a chat bubble.
        """
        
        response = client.models.generate_content(model="gemini-2.5-flash", contents=chat_prompt)
        return jsonify({"response": response.text})
    except Exception as e:
        print(f"Chat Error: {e}")
        return jsonify({"response": "Sorry, I am having trouble connecting to the AI right now. Please check your API key."})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/planner')
def planner_redirect():
    return index()

@app.route('/plan', methods=['GET', 'POST'])
def plan():
    if request.method == 'GET':
        return index()

    if request.method == 'POST':
        # Use Global Client
        if not client:
             print("ERROR: GENAI_API_KEY is missing/empty")
             return render_template('planner.html', error="Gemini API Key is missing. Please check .env file.")

        destination = request.form.get('destination')
        days = request.form.get('days')
        budget = request.form.get('budget')
        
        # Handle Interests (Checkbox list)
        interests_list = request.form.getlist('interests')
        interests = ", ".join(interests_list) if interests_list else "General Sightseeing"
        
        # Handle Travelers
        travelers_type = request.form.get('travelers_type')
        travelers_count = request.form.get('travelers_count')
        
        if travelers_type == "Solo":
            travelers = "Solo Traveler"
        elif travelers_type == "Couple":
            travelers = "Couple (2 People)"
        else:
            travelers = f"{travelers_type} group of {travelers_count} People"

        if not destination or not days:
            return "Please provide destination and duration.", 400

        if not GENAI_API_KEY:
             return render_template('planner.html', error="Gemini API Key is missing. Please add it to your .env file and restart the server.")

        data = get_gemini_recommendations(destination, days, budget, interests, travelers)

        if data:
            print(f"Generated Keys: {data.keys()}")
            
            # Define fallback images for categories
            category_fallbacks = {
                "hotel": "https://images.unsplash.com/photo-1566073771259-6a8506099945?q=80&w=2070&auto=format&fit=crop",
                "place": "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?q=80&w=2070&auto=format&fit=crop",
                "food": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w=2070&auto=format&fit=crop"
            }

            # Collect all image queries with their respective categories
            image_tasks = []
            
            # Hotels
            for hotel in data.get('hotels', []):
                image_tasks.append({
                    "item": hotel,
                    "query": f"{hotel['name']} {destination}",
                    "category": "hotel"
                })
            
            # Places
            for day in data.get('itinerary', []):
                for place in day.get('places', []):
                    image_tasks.append({
                        "item": place,
                        "query": f"{place['name']} {destination}",
                        "category": "place"
                    })
            
            # Food
            for food in data.get('food', []):
                image_tasks.append({
                    "item": food,
                    "query": f"{food['name']} {destination}",
                    "category": "food"
                })
            
            def fetch_item_image(task):
                item = task["item"]
                query = task["query"]
                category = task["category"]
                item_name = item.get('name', '').lower()
                
                # Override category if name strongly suggests it (e.g. itinerary stop for food)
                if any(word in item_name for word in ['restaurant', 'dining', 'bhandar', 'cafe', 'food', 'stall', 'bakery', 'thali', 'lunch', 'dinner']):
                    category = 'food'
                elif any(word in item_name for word in ['hotel', 'resort', 'stay', 'inn', 'hostel']):
                    category = 'hotel'
                
                # Try specific query with city context
                img = get_wiki_image(item.get('name'), destination)
                
                # If failed, try name only
                if not img:
                    img = get_wiki_image(item.get('name'))
                
                # If still failed, use LoremFlickr which is more reliable for keyword placeholding
                if not img:
                    # Append a random seed to URL for variety
                    seed = hash(item.get('name', '')) % 1000
                    # Standardizing keywords for LoremFlickr
                    clean_dest = destination.replace(' ', ',')
                    img = f"https://loremflickr.com/600/400/{category},{clean_dest}/all?lock={seed}"

                return item, img

            with ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(fetch_item_image, image_tasks))
            
            # Assign images back
            for item, img in results:
                item['image'] = img

            return render_template('planner.html', data=data, destination=destination)
        else:
            # Check if there's a specific error log
            error_details = "Failed to generate itinerary. This might be due to API safety filters or an invalid key."
            if os.path.exists("generation_error.log"):
                with open("generation_error.log", "r") as f:
                    lines = f.readlines()
                    if lines:
                        error_details += f" (Details: {lines[-1].strip()})"
            
            return render_template('planner.html', error=error_details)
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)



