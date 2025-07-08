import asyncio
import os
import csv
import json
import unicodedata
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from dotenv import load_dotenv
from dataclasses import dataclass

load_dotenv()

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")


@dataclass
class Rider:
    name: str
    team: str
    dnf: bool
    cost: int
    gc_points: int
    mountain_points: int
    sprint_points: int
    young_gc_points: int | str
    points: int
    is_kluns: bool


async def login(page):
    await page.goto("https://www.sportpools.net/nl/login")
    await page.fill("input[name='username']", USERNAME)
    await page.fill("input[name='password']", PASSWORD)
    await page.check("input[name='remember']")
    await page.click("button[type='submit']")
    await page.wait_for_load_state("networkidle")
    print("✅ Logged in successfully.")


def normalize_text(text):
    """Convert accented characters to their basic forms (é -> e, ã -> a, etc.)"""
    if not text:
        return ""

    # First try to fix common encoding issues
    try:
        # Try to decode/encode to fix mojibake
        if "Ã" in text or "Ä" in text or "Ã©" in text:
            # Common mojibake patterns - try to fix them
            text = text.replace("Ã©", "é").replace("Ã¡", "á").replace("Ã­", "í")
            text = text.replace("Ã³", "ó").replace("Ãº", "ú").replace("Ã±", "ñ")
            text = text.replace("Ã§", "ç").replace("Ã¨", "è").replace("Ã ", "à")
            text = text.replace("Ã´", "ô").replace("Ã¢", "â").replace("Ã«", "ë")
            text = text.replace("Ã¯", "ï").replace("Ã¼", "ü").replace("Ã¤", "ä")
            text = text.replace("Ã¶", "ö").replace("Ã…", "Å").replace("Ã˜", "Ø")
            text = text.replace("Ä", "c").replace("Ä", "C")
    except:
        pass

    # Remove accents and normalize to ASCII
    try:
        # Normalize to NFD (decomposed form)
        normalized = unicodedata.normalize("NFD", text)
        # Filter out combining characters (accents)
        ascii_text = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
        return ascii_text
    except:
        # If all else fails, return original text
        return text


def parse_rider_row(row, is_last_rider=False) -> Rider:
    name_element = row.select_one("span.font-weight-medium")
    name = name_element.get_text(strip=True) if name_element else ""
    name = normalize_text(name)

    team_span = row.select_one("span.d-block.text-sm.text-nowrap")
    team = team_span.get_text(strip=True) if team_span else ""
    team = normalize_text(team)

    dnf_span = row.select_one("span.text-nowrap.pl-10")
    dnf = "DNF" in dnf_span.get_text() if dnf_span else False

    stat_ul = row.select_one("ul.list-none.list-inline.m-0.text-nowrap")
    stats = (
        [li.get_text(strip=True).replace(".", "") for li in stat_ul.select("li")]
        if stat_ul
        else []
    )
    stats = [x.split(" ")[0].split("\n")[0] for x in stats]
    stats = [int(s) if s.isdigit() else s for s in stats]
    while len(stats) < 6:
        stats.append(0)  # pad with zeros

    return Rider(
        name=name,
        team=team,
        dnf=dnf,
        cost=stats[0],
        gc_points=stats[1],
        mountain_points=stats[2],
        sprint_points=stats[3],
        young_gc_points=stats[4],
        points=stats[5],
        is_kluns=is_last_rider,
    )


async def get_riders_for_team(page, team_url) -> list[Rider]:
    await page.goto(team_url)

    # Set proper encoding for the page
    await page.set_extra_http_headers({"Accept-Charset": "utf-8"})

    content = await page.content()
    soup = BeautifulSoup(content, "html.parser", from_encoding="utf-8")

    riders = []
    rider_rows = soup.select("div.w-100.d-flex.align-items-center")

    print(f"   Found {len(rider_rows)} riders for this team")

    for i, row in enumerate(rider_rows):
        try:
            # The last rider is the "kluns"
            is_last_rider = i == len(rider_rows) - 1
            rider = parse_rider_row(row, is_last_rider)
            riders.append(rider)
            print(f"   Rider {i + 1}: {rider.name} (Kluns: {rider.is_kluns})")
        except Exception as e:
            print(f"⚠️ Skipping row due to error: {e}")

    return riders


async def fetch_api_data(page, pool_id, subleague_id, page_num):
    """Fetch data from the API endpoint"""
    api_url = f"https://www.sportpools.net/api/cycling/pools/{pool_id}/subleagues/{subleague_id}/signups?page={page_num}"

    try:
        # Use Playwright to fetch the API since we need authentication
        response = await page.goto(api_url)
        if response.status == 200:
            content = await page.content()
            # Extract JSON from the page content (it should be the entire page content)
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start != -1 and json_end != -1:
                json_content = content[json_start:json_end]
                # Parse with proper encoding handling
                return json.loads(json_content, strict=False)
        else:
            print(f"⚠️ API request failed with status: {response.status}")
            return None
    except Exception as e:
        print(f"⚠️ Error fetching API data for page {page_num}: {e}")
        return None


async def get_all_users_from_api(page, pool_id, subleague_id) -> dict[str, str]:
    """Get all users and their team URLs using the API"""
    all_users = {}
    page_num = 1

    while True:
        print(f"📡 Fetching API data for page {page_num}...")

        api_data = await fetch_api_data(page, pool_id, subleague_id, page_num)
        if not api_data or "data" not in api_data:
            print(f"⚠️ No data found for page {page_num}")
            break

        users_on_page = api_data["data"]
        print(f"   Found {len(users_on_page)} users on page {page_num}")

        # Extract username and team URL for each user
        for user_data in users_on_page:
            signup = user_data.get("signup", {})
            user_info = signup.get("user", {})
            username = user_info.get("username", "")
            team_url = signup.get("selectionUrl", "")

            if username and team_url:
                all_users[username] = team_url

        # Check if this is the last page
        last_page = api_data.get("lastPage", 1)
        if page_num >= last_page:
            print(f"✅ Reached last page ({last_page})")
            break

        page_num += 1

        # Safety check to avoid infinite loops
        if page_num > 50:  # Adjust as needed
            print("⚠️ Reached maximum page limit (50). Stopping.")
            break

    return all_users


async def crawl_subleague_teamurls(subleague_url) -> dict[str, list[Rider]]:
    # Extract pool_id and subleague_id from the URL
    # URL format: https://www.sportpools.net/nl/tour-de-france/2025/klassementen/subleague/2154
    parts = subleague_url.split("/")
    subleague_id = parts[-1]  # 2154

    # For Tour de France 2025, the pool ID appears to be 246 based on your API example
    # You might need to adjust this if it's different
    pool_id = 246

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()

        await login(page)

        print(
            f"🔍 Getting all users from API (pool: {pool_id}, subleague: {subleague_id})..."
        )

        # Get all user-team mappings using the API
        name_url_map = await get_all_users_from_api(page, pool_id, subleague_id)

        print(f"📊 Found {len(name_url_map)} users total")

        # Now crawl each team
        user_riders = {}
        for i, (name, url) in enumerate(name_url_map.items(), 1):
            print(f"🔍 Crawling team for {name} ({i}/{len(name_url_map)})...")
            riders = await get_riders_for_team(page, url)
            user_riders[name] = riders

            # Debug: Show kluns info for first few teams
            if i <= 3:
                kluns_riders = [r for r in riders if r.is_kluns]
                print(
                    f"   Team {name} has {len(kluns_riders)} kluns riders: {[r.name for r in kluns_riders]}"
                )

        await browser.close()
        return user_riders


def export_to_csv(user_riders: dict[str, list[Rider]], filename="riders.csv"):
    with open(filename, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Gebruiker",
                "Renner",
                "Team",
                "Uitgevallen",
                "Kosten",
                "Eind",
                "Berg",
                "Sprint",
                "Jongeren",
                "Punten",
                "Kluns",
            ]
        )
        for user, riders in user_riders.items():
            for r in riders:
                writer.writerow(
                    [
                        user,
                        r.name,
                        r.team,
                        "Ja" if r.dnf else "Nee",
                        r.cost,
                        r.gc_points,
                        r.mountain_points,
                        r.sprint_points,
                        r.young_gc_points
                        if isinstance(r.young_gc_points, int)
                        else "-",
                        r.points,
                        "Ja" if r.is_kluns else "Nee",
                    ]
                )
    print(f"📁 CSV exported to {filename}")


if __name__ == "__main__":
    s_url = (
        "https://www.sportpools.net/nl/tour-de-france/2025/klassementen/subleague/2154"
    )
    user_riders = asyncio.run(crawl_subleague_teamurls(subleague_url=s_url))

    for user, riders in user_riders.items():
        print(f"\n👤 {user}'s team:")
        for r in riders:
            print(f"  - {r.name} ({r.team}) → {r.points} pts")

    export_to_csv(user_riders)
