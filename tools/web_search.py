"""
Web Search Tool — uses DuckDuckGo (free, no API key required).
"""

from langchain_core.tools import tool
from ddgs import DDGS
from config.settings import WEB_SEARCH_MAX_RESULTS


@tool
def search_web(query: str, max_results: int = None) -> str:
    """Search the web using DuckDuckGo. Returns titles, snippets, and URLs.
    Use this when you need current information, facts, documentation, or tutorials.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default from config).
    """
    if max_results is None:
        max_results = WEB_SEARCH_MAX_RESULTS

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return f"No results found for: {query}"

        output = []
        for i, r in enumerate(results, 1):
            output.append(
                f"[{i}] {r.get('title', 'No title')}\n"
                f"    URL: {r.get('href', 'N/A')}\n"
                f"    {r.get('body', 'No snippet')}\n"
            )
        return "\n".join(output)

    except Exception as e:
        return f"Search error: {str(e)}"


@tool
def search_news(query: str, max_results: int = 5) -> str:
    """Search for recent news articles using DuckDuckGo News.
    Use this when the user asks about current events or recent developments.

    Args:
        query: The news search query.
        max_results: Maximum number of news results.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results))

        if not results:
            return f"No news found for: {query}"

        output = []
        for i, r in enumerate(results, 1):
            output.append(
                f"[{i}] {r.get('title', 'No title')}\n"
                f"    Source: {r.get('source', 'Unknown')}\n"
                f"    Date: {r.get('date', 'Unknown')}\n"
                f"    URL: {r.get('url', 'N/A')}\n"
                f"    {r.get('body', 'No snippet')}\n"
            )
        return "\n".join(output)

    except Exception as e:
        return f"News search error: {str(e)}"
