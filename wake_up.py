import streamlit as st
import asyncio
from playwright.async_api import async_playwright
from site_manager import projects


urls = [p['url'] for p in projects]

async def wake_up_apps(urls):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        results = []
        
        for url in urls:
            try:
                # We just need to hit the URL and wait a few seconds for the "Wake up"
                await page.goto(url, timeout=60000) 
                # Give it 5 seconds to ensure the 'booting' process finishes
                await asyncio.sleep(5) 
                results.append(f"✅ {url} is awake!")
            except Exception as e:
                results.append(f"❌ {url} failed: {str(e)}")
        
        await browser.close()
        return results

st.title("⚡ Portfolio Awakener")
st.write("Click below to ensure all projects are 'warm' and ready for recruiters.")

if st.button("🚀 Wake Up All Apps"):
    with st.spinner("Pinging servers..."):
        status = asyncio.run(wake_up_apps(urls))
        for s in status:
            st.write(s)
