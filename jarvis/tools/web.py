import webbrowser
from urllib.parse import quote_plus

from .registry import tool


@tool()
def open_url(url: str) -> str:
    """Open a web address in the default browser."""
    if "://" not in url:
        url = "https://" + url
    if not url.startswith(("http://", "https://")):
        raise ValueError("only http and https addresses are allowed")
    webbrowser.open(url)
    return f"Opened {url}"


@tool()
def web_search(query: str) -> str:
    """Open a web search for the query in the default browser."""
    webbrowser.open("https://duckduckgo.com/?q=" + quote_plus(query))
    return f"Opened a search for {query}"
