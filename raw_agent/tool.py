from urllib.parse import quote

import requests
from loguru import logger

# you should change this header to your own
headers = {
        "User-Agent": "agent_no_framework/1.0 (+https://example.com/contact)"
    }

def get_weather(location: str) -> str:
    try:
        safe_location = quote(location.strip())
        response = requests.get(f"https://wttr.in/{safe_location}?format=1", timeout=10)
        if response.status_code == 200:
            return response.text.strip()
        else:
            return f"Could not find weather for '{location}'."
    except Exception as e:
        return f"Error fetching weather: {str(e)}"


def search_location_info(location: str) -> str:

    if not location or not location.strip():
        return "Please provide a location."

    try:
        q = location.strip()
        # Search Wikipedia
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "list": "search", "srsearch": q, "srlimit": 1, "format": "json"},
            headers=headers,
            timeout=10,
        )
        if not r.ok:
            logger.debug(f"Search failed for '{q}'.")
            logger.debug(r)
            return f"Search failed for '{q}'."
        data = r.json()
        results = data.get("query", {}).get("search", [])
        if not results:
            logger.debug(f"No Wikipedia result for '{q}'.")
            return f"No Wikipedia result for '{q}'."

        title = results[0].get("title") or q
        # Fetch summary
        r2 = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "prop": "extracts|coordinates|info", "exintro": 1, "explaintext": 1,
                    "titles": title, "format": "json", "inprop": "url"},
            headers=headers,
            timeout=10,
        )
        if not r2.ok:
            return f"Lookup failed for '{title}'."
        d2 = r2.json()
        page = next(iter(d2.get("query", {}).get("pages", {}).values()), {})
        summary = (page.get("extract") or "").strip()
        coords = (page.get("coordinates") or [{}])[0]
        lat, lon = coords.get("lat"), coords.get("lon")
        url = page.get("fullurl") or f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"

        lines = [title, summary]
        if lat and lon:
            lines.append(f"Coordinates: {lat}, {lon}")
        lines.append(f"URL: {url}")
        return "\n".join(lines)

    except Exception as e:
        return f"Error: {e}"
