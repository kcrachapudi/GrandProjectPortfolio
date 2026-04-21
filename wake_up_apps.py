import asyncio
from playwright.async_api import async_playwright

APP_URLS = ["https://bioinform1.streamlit.app/"]

async def wake_apps():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for url in APP_URLS:
            print(f"Checking {url}...")
            try:
                # 1. Increase timeout to wait for the slow sleep-screen to load
                await page.goto(url, wait_until="networkidle", timeout=90000)
                
                # 2. Search for common 'Sleep' markers: "Zzzz" or the specific button
                # We use a broad search for the button text used by Streamlit
                wake_button = page.get_by_role("button", name="Yes, get this app back up!")
                
                if await wake_button.is_visible():
                    print(f"Detected Zzz screen for {url}. Clicking wake button...")
                    await wake_button.click()
                    # 3. CRITICAL: Wait 30s for the actual Python engine to boot
                    # A quick click-and-leave often fails to establish the WebSocket
                    await asyncio.sleep(30) 
                    print(f"Wake signal sent to {url}.")
                else:
                    # Check for "Zzzz" text just in case the button role is different
                    content = await page.content()
                    if "Zzzz" in content or "asleep" in content:
                        print(f"Page looks asleep but button not found. Trying manual click...")
                        # Fallback: click any button that looks like a wake button
                        await page.click("button:has-text('back up')")
                        await asyncio.sleep(30)
                    else:
                        print(f"{url} appears genuinely awake.")
            except Exception as e:
                print(f"Error during wake-up for {url}: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(wake_apps())
