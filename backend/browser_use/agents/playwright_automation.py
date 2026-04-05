from playwright.async_api import async_playwright
from backend.browser_use.agents.browser_use_client import get_browseruse_client


async def extract_menu_section_with_playwright(url: str) -> dict:
    client = get_browseruse_client()
    browser = await client.browsers.create()

    try:
        async with async_playwright() as p:
            pw_browser = await p.chromium.connect_over_cdp(browser.cdp_url)

            contexts = pw_browser.contexts
            if not contexts or not contexts[0].pages:
                await pw_browser.close()
                return {"page_title": None, "body_text": None}

            page = contexts[0].pages[0]

            await page.goto(url, timeout=30000)

            title = await page.title()
            body_text = await page.locator("body").inner_text()

        return {
            "page_title": title,
            "body_text": body_text,
        }
    finally:
        await client.browsers.stop(browser.id)