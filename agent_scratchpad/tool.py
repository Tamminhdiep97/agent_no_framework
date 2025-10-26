import requests
from urllib.parse import quote, urlparse
from loguru import logger
from ddgs import DDGS

import config as cfg


headers = {
    "User-Agent": "agent_no_framework/1.0 (+https://example.com/contact)"
}

# ======================
# NEWS TOOLS (uses NewsAPI if key provided, else falls back to Wikipedia)
# ======================


def fetch_webpage_summary(query: str) -> str:
    """
    Search using DuckDuckGo and return a summary of the results
    The query parameter can be a domain, topic, or search query
    """
    try:
        # If it looks like a URL, extract the domain/topic, otherwise treat as search query
        if query.startswith(('http://', 'https://')):
            parsed = urlparse(query)
            if parsed.netloc not in cfg.ALLOWED_DOMAINS:
                return f"URL domain not allowed for search: {parsed.netloc}"
            search_query = f"{parsed.netloc} {parsed.path.replace('/', ' ')}".strip()
        else:
            search_query = query
        logger.info(f"query: {query}")
        # Perform DuckDuckGo search using ddgs
        ddgs = DDGS()
        results = ddgs.text(search_query, max_results=3)

        if not results:
            return f"No search results found for: {search_query}"

        # Extract the most relevant result
        summary_parts = []

        # Take top 2 results
        for i, result in enumerate(results[:2]):
            title = result.get('title', 'No title')
            body = result.get('body', 'No content')
            href = result.get('href', 'No URL')
            summary_parts.append(f"Result {i+1}: {title}\nSnippet: {body}\nURL: {href}")

        return "DuckDuckGo Search Results:\n" + "\n".join(summary_parts)
    except Exception as e:
        return f"ERROR with DuckDuckGo search for '{query}': {str(e)}"


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
# MATH TOOLS
# ======================

def add_numbers(a: float, b: float) -> str:
    """Add two numbers together"""
    result = a + b
    return f"The sum of {a} and {b} is {result}"


def subtract_numbers(a: float, b: float) -> str:
    """Subtract second number from first number"""
    result = a - b
    return f"{a} minus {b} equals {result}"


def multiply_numbers(a: float, b: float) -> str:
    """Multiply two numbers"""
    result = a * b
    return f"{a} times {b} equals {result}"


def divide_numbers(a: float, b: float) -> str:
    """Divide first number by second number"""
    if b == 0:
        return "Error: Cannot divide by zero"
    result = a / b
    return f"{a} divided by {b} equals {result}"
