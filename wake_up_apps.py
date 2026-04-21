import asyncio
from playwright.async_api import async_playwright
from site_urls import projects

APP_URLS = [p['url'] for p in projects]

async def wake_apps():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for url in APP_URLS:
            print(f"Checking {url}...")
            try:
                await page.goto(url, timeout=60000)
                # Look for the 'Yes, get this app back up!' button
                # Streamlit uses a specific button for this
                wake_button = page.get_by_role("button", name="Yes, get this app back up!")
                
                if await wake_button.is_visible():
                    print(f"Found sleep screen for {url}. Clicking wake button...")
                    await wake_button.click()
                    # Wait 15 seconds for it to actually boot up
                    await asyncio.sleep(15)
                else:
                    print(f"{url} is already awake.")
            except Exception as e:
                print(f"Error pinging {url}: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(wake_apps())
