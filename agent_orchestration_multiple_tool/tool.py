import requests
from urllib.parse import quote
from loguru import logger

import config as cfg


headers = {
    "User-Agent": "agent_no_framework/1.0 (+https://example.com/contact)"
}

# ======================
# NEWS TOOLS (uses NewsAPI if key provided, else falls back to Wikipedia)
# ======================


def get_top_headlines() -> str:
    if cfg.NEWS_API_KEY:
        try:
            r = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={"country": "us", "apiKey": cfg.NEWS_API_KEY},
                timeout=10,
            )
            if r.ok:
                articles = r.json().get("articles", [])
                if articles:
                    title = articles[0].get("title", "No title")
                    source = articles[0].get("source", {}).get("name", "Unknown")
                    return f"Top headline: {title} — {source}"
        except Exception as e:
            logger.warning(f"NewsAPI error: {e}")
    # Fallback: use Wikipedia "In the news"
    try:
        r = requests.get("https://en.wikipedia.org/wiki/Main_Page", headers=headers, timeout=10)
        if r.ok and "In the news" in r.text:
            lines = r.text.split("In the news")[1].split("<ul>")[1].split("</ul>")[0].split("</li>")
            if lines:
                first = lines[0].split(">")[-1].strip()
                return f"Top headline (from Wikipedia): {first}"
    except Exception as e:
        logger.warning(f"Wikipedia fallback failed: {e}")
    return "Unable to fetch top headlines."

def search_news_articles(query: str) -> str:
    if cfg.NEWS_API_KEY:
        try:
            r = requests.get(
                "https://newsapi.org/v2/everything",
                params={"q": query, "sortBy": "relevancy", "apiKey": cfg.NEWS_API_KEY},
                timeout=10,
            )
            if r.ok:
                articles = r.json().get("articles", [])
                if articles:
                    title = articles[0].get("title", "No title")
                    desc = articles[0].get("description", "No description")
                    url = articles[0].get("url", "")
                    return f"News: {title}\n{desc}\n{url}"
        except Exception as e:
            logger.warning(f"NewsAPI search error: {e}")
    return f"No recent news found for '{query}'."

def get_news_source_info(source: str) -> str:
    # Use Wikipedia to get info about the source
    try:
        q = f"{source} (news organization)"
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": q,
                "srlimit": 1,
                "format": "json"
            },
            headers=headers,
            timeout=10,
        )
        if r.ok:
            data = r.json()
            results = data.get("query", {}).get("search", [])
            if results:
                title = results[0]["title"]
                r2 = requests.get(
                    "https://en.wikipedia.org/w/api.php",
                    params={
                        "action": "query",
                        "prop": "extracts",
                        "exintro": 1,
                        "explaintext": 1,
                        "titles": title,
                        "format": "json"
                    },
                    headers=headers,
                    timeout=10,
                )
                if r2.ok:
                    page = next(iter(r2.json()["query"]["pages"].values()))
                    extract = page.get("extract", "").split(".")[0] + "."
                    url = f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
                    return f"{extract} More: {url}"
    except Exception as e:
        logger.warning(f"Source info error: {e}")
    return f"Could not find information about '{source}'."

# ======================
# HEALTH TOOLS
# ======================

def get_nutrition_info(food: str) -> str:
    if cfg.EDAMAM_APP_ID and cfg.EDAMAM_APP_KEY:
        try:
            r = requests.get(
                "https://api.edamam.com/api/nutrition-data",
                params={
                    "ingr": food,
                    "app_id": cfg.EDAMAM_APP_ID,
                    "app_key": cfg.EDAMAM_APP_KEY
                },
                timeout=10,
            )
            if r.ok:
                data = r.json()
                if data.get("calories", 0) > 0:
                    cal = data["calories"]
                    nutrients = data.get("totalNutrients", {})
                    protein = nutrients.get("PROCNT", {}).get("quantity", 0)
                    fat = nutrients.get("FAT", {}).get("quantity", 0)
                    carbs = nutrients.get("CHOCDF", {}).get("quantity", 0)
                    return (
                        f"{food.capitalize()}: {cal} kcal | "
                        f"Protein: {protein:.1f}g | Fat: {fat:.1f}g | Carbs: {carbs:.1f}g"
                    )
        except Exception as e:
            logger.warning(f"Edamam error: {e}")
    # Fallback: use USDA public data via open food facts (no key)
    try:
        r = requests.get(
            "https://world.openfoodfacts.org/cgi/search.pl",
            params={"search_terms": food, "search_simple": 1, "json": 1},
            timeout=10,
        )
        if r.ok:
            data = r.json()
            products = data.get("products", [])
            if products:
                p = products[0]
                name = p.get("product_name", food)
                energy = p.get("energy_100g", "N/A")
                return f"{name}: ~{energy} kJ per 100g (from Open Food Facts)."
    except Exception as e:
        logger.warning(f"Open Food Facts fallback failed: {e}")
    return f"Nutrition info for '{food}' not available."

def check_symptom(symptom: str) -> str:
    # Use OpenFDA or NIH MedlinePlus (public)
    # Simple approach: link to MedlinePlus search
    safe_symptom = quote(symptom)
    return (
        f"For '{symptom}', see trusted medical info: "
        f"https://medlineplus.gov/search/?query={safe_symptom}"
    )

def find_local_clinics(location: str) -> str:
    # Use OpenStreetMap Overpass API (no key needed)
    try:
        query = """
        [out:json];
        area["ISO3166-1"="US"]->.searchArea;
        (
          node["amenity"="clinic"](area.searchArea)["name"](around:5000,0,0);
          node["amenity"="hospital"](area.searchArea)["name"](around:5000,0,0);
        );
        out body;
        """
        # First, geocode location to lat/lon
        geo = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": location, "format": "json", "limit": 1},
            headers=headers,
            timeout=10,
        )
        if not geo.ok or not geo.json():
            return f"Could not geocode location: {location}"
        loc = geo.json()[0]
        lat, lon = loc["lat"], loc["lon"]

        # Now search for clinics near lat,lon
        overpass_url = "https://overpass-api.de/api/interpreter"
        overpass_query = f"""
        [out:json];
        (
          node["amenity"~"clinic|hospital"]["name"](around:10000,{lat},{lon});
        );
        out 5;
        """
        r = requests.post(overpass_url, data=overpass_query, timeout=15)
        if r.ok:
            data = r.json()
            elements = data.get("elements", [])
            if elements:
                names = [e.get("tags", {}).get("name", "Unnamed") for e in elements[:3]]
                return f"Clinics/hospitals near {location}:\n- " + "\n- ".join(names)
            else:
                return f"No clinics found near {location}."
        else:
            return f"Search failed for {location}."
    except Exception as e:
        logger.warning(f"Clinic search error: {e}")
        return f"Unable to find clinics near {location}."
