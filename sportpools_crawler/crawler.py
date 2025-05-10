import asyncio
import os
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from dotenv import load_dotenv


load_dotenv()  # Load from .env file

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")


async def login(page):
    await page.goto("https://www.sportpools.net/nl/login")

    # Fill in login credentials
    await page.fill("input[name='username']", USERNAME)
    await page.fill("input[name='password']", PASSWORD)

    # Tick 'remember me'
    await page.check("input[name='remember']")

    # Submit the form (assumes there's a button with type submit)
    await page.click("button[type='submit']")

    # Wait for redirect / page load after login
    await page.wait_for_load_state("networkidle")

    print("✅ Logged in successfully.")


async def get_team_urls():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()

        # Log in first
        await login(page)

        await page.goto(
            "https://www.sportpools.net/nl/giro-italia/2025/klassementen/subleague/2154"
        )

        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")

        name_url_map = {}
        for td in soup.find_all("td"):
            img_tag = td.find("img")
            a_tag = td.find("a")
            if img_tag and a_tag:
                name = a_tag.get_text(strip=True)
                href = a_tag.get("href")
                if name and href:
                    name_url_map[name] = href

        await browser.close()
        return name_url_map


if __name__ == "__main__":
    user_teamurl_mapping = asyncio.run(get_team_urls())
    print(user_teamurl_mapping)
