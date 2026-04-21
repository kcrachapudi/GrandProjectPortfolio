import asyncio
from playwright.async_api import async_playwright
from site_manager import projects


APP_URLS = [p['url'] for p in projects]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        for url in APP_URLS:
            print(f"Waking up {url}...")
            await page.goto(url)
            await asyncio.sleep(10) # Give it time to boot
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
