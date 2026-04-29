import asyncio
from playwright.async_api import async_playwright

APP_URLS = [
            "https://stockmarketperformanceandforecastingengine.streamlit.app/",
            "https://medistream-ai-ready-medical-imaging-pipeline.streamlit.app/",
            "https://smartcreditriskloaneligibilityengine.streamlit.app/",
            "https://bioinform1.streamlit.app/",             
            "https://real-timetransactionfrauddetectionsystem.streamlit.app/",
            "https://bioinform2.streamlit.app/", 
            "https://rad-kalyan-rachapudi-recruiter.streamlit.app/"]

async def wake_apps():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for url in APP_URLS:
            print(f"Checking {url}...", flush=True)
            try:
                page = await browser.new_page()
                # 1. Increase timeout to wait for the slow sleep-screen to load
                await page.goto(url, wait_until="domcontentloaded", timeout=90000)
                
                # 2. Search for common 'Sleep' markers: "Zzzz" or the specific button
                # We use a broad search for the button text used by Streamlit
                wake_button = page.get_by_role("button", name="Yes, get this app back up!")
                
                if await wake_button.is_visible():
                    print(f"Detected Zzz screen for {url}. Clicking wake button...", flush=True)
                    await wake_button.click()
                    # 3. CRITICAL: Wait 30s for the actual Python engine to boot
                    # A quick click-and-leave often fails to establish the WebSocket
                    await asyncio.sleep(30) 
                    print(f"Wake signal sent to {url}.", flush=True)
                else:
                    # Check for "Zzzz" text just in case the button role is different
                    content = await page.content()
                    if "Zzzz" in content or "asleep" in content:
                        print(f"Page looks asleep but button not found. Trying manual click...")
                        # Fallback: click any button that looks like a wake button
                        await page.click("button:has-text('back up')")
                        await asyncio.sleep(10)
                    else:
                        print(f"{url} appears genuinely awake.", flush=True)
            except Exception as e:
                print(f"Error during wake-up for {url}: {e}", flush=True)
            await page.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(wake_apps())
