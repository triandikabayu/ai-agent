"""
Web Scraper Tool — extracts clean text content from modern web pages.

Primary:  Playwright (headless Chromium) — handles JS-rendered SPAs securely and natively extracts DOM innerText.
Fallback: Selectolax + requests — high performance parsing for simple static pages.
"""

import re
import requests
from langchain_core.tools import tool
from selectolax.parser import HTMLParser
from config.settings import MAX_SCRAPE_LENGTH

# ---------------------------------------------------------------------------
# Selectolax scraper (fallback — for simple static pages, ultra-fast)
# ---------------------------------------------------------------------------

def _scrape_with_selectolax(url: str) -> str:
    """Fallback scraper using requests + Selectolax for fast static page parsing."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    # High performance HTML parsing
    tree = HTMLParser(response.text)
    
    # Remove unwanted tags completely (fast)
    tags_to_remove = ["script", "style", "nav", "footer", "header", "aside", 
                      "noscript", "iframe", "svg", "form", "button", 
                      "img", "video", "audio", "canvas", "meta", "link", "[aria-hidden='true']"]
    
    for selector in tags_to_remove:
        for node in tree.css(selector):
            node.decompose()
            
    # Target main content areas
    main_node = tree.css_first("main, article, [role='main'], #content, .content, .main")
    if not main_node:
        main_node = tree.css_first("body") or tree
        
    if hasattr(main_node, "text"):
        # Selectolax allows extracting text directly, stripping extra whitespace
        text = main_node.text(separator='\n', strip=True) 
        # Clean up excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
        
    return ""

# ---------------------------------------------------------------------------
# Playwright scraper (primary — handles JS-rendered sites)
# ---------------------------------------------------------------------------

def _scrape_with_playwright(url: str) -> str:
    """
    Scrape a page using headless Chromium via Playwright.
    Executes in the browser native DOM engine. Memory-optimized by blocking media/assets.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 KHTML, like Gecko Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
        )
        page = context.new_page()

        # Route interceptor to aggressively block non-essential resources (saves memory/bandwidth)
        def route_intercept(route):
            if route.request.resource_type in ["image", "media", "font", "stylesheet", "other"]:
                route.abort()
            else:
                route.continue_()

        page.route("**/*", route_intercept)

        try:
            # Navigate and wait for the page bare minimum to be fully loaded
            page.goto(url, wait_until="load", timeout=30000)

            # Give a tiny buffer for client-side hydration (e.g. React/Next.js)
            page.wait_for_timeout(1000)

            # Extract text completely natively within the browser engine using JS evaluated script
            # No Python string passing or Python HTML parsing required
            text = page.evaluate("""() => {
                // 1. Remove junk elements directly from the DOM
                const selectors = [
                    'script', 'style', 'nav', 'header', 'footer', 'aside', 
                    'iframe', '[aria-hidden="true"]', 'noscript', 'dialog', 'form'
                ];
                selectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => el.remove());
                });
                
                // 2. Identify main content container
                const main = document.querySelector('main, article, [role="main"], #content, .content, .main') || document.body;
                
                // 3. Return native clean text content
                return main.innerText;
            }""")
            
            # Clean up JS output
            return re.sub(r'\n{3,}', '\n\n', text).strip()

        finally:
            context.close()
            browser.close()


# ---------------------------------------------------------------------------
# Public tool
# ---------------------------------------------------------------------------

@tool
def scrape_url(url: str, use_browser: bool = True) -> str:
    """Scrape a web page and extract its text content.
    Uses a highly memory-optimized headless browser (Playwright) by default, extracting 
    natively to handle modern JS-rendered sites like React docs, Next.js, MDN, etc.
    
    Args:
        url: The full URL of the page to scrape (must start with http:// or https://).
        use_browser: If True (default), use Playwright headless browser for JS-rendered pages.
                     If False, use lightning-fast Selectolax for static HTML pages.
    """
    if not url.startswith(("http://", "https://")):
        return "Error: URL must start with http:// or https://"

    try:
        content = None

        if use_browser:
            try:
                content = _scrape_with_playwright(url)
            except Exception as e:
                # If Playwright fails, fall back to Selectolax
                print(f"[Warning] Playwright failed, falling back to Selectolax: {e}")
                content = None

        if not content:
            try:
                content = _scrape_with_selectolax(url)
            except Exception as e:
                return f"Error scraping {url}: {str(e)}"

        if not content or len(content.strip()) < 50:
            return f"Error: Could not extract meaningful content from {url}"

        # Truncate if too long to save context window memory
        if len(content) > MAX_SCRAPE_LENGTH:
            content = content[:MAX_SCRAPE_LENGTH] + "\n\n... [Content truncated]"

        return f"--- Content from {url} ---\n\n{content}"

    except Exception as e:
        return f"Error scraping {url}: {str(e)}"
