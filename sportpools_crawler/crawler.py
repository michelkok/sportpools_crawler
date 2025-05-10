import asyncio
import os
import csv
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


async def login(page):
    await page.goto("https://www.sportpools.net/nl/login")
    await page.fill("input[name='username']", USERNAME)
    await page.fill("input[name='password']", PASSWORD)
    await page.check("input[name='remember']")
    await page.click("button[type='submit']")
    await page.wait_for_load_state("networkidle")
    print("✅ Logged in successfully.")


def parse_rider_row(row) -> Rider:
    name = row.select_one("span.font-weight-medium").get_text(strip=True)
    team_span = row.select_one("span.d-block.text-sm.text-nowrap")
    team = team_span.get_text(strip=True) if team_span else ""

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
    )


async def get_riders_for_team(page, team_url) -> list[Rider]:
    await page.goto(team_url)
    content = await page.content()
    soup = BeautifulSoup(content, "html.parser")

    riders = []
    for row in soup.select("div.w-100.d-flex.align-items-center"):
        try:
            rider = parse_rider_row(row)
            riders.append(rider)
        except Exception as e:
            print(f"⚠️ Skipping row due to error: {e}")

    return riders


async def crawl_subleague_teamurls(subleague_url) -> dict[str, list[Rider]]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()

        await login(page)
        await page.goto(subleague_url)
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
                    full_url = (
                        "https://www.sportpools.net" + href
                        if href.startswith("/")
                        else href
                    )
                    name_url_map[name] = full_url

        user_riders = {}
        for name, url in name_url_map.items():
            print(f"🔍 Crawling team for {name} ...")
            riders = await get_riders_for_team(page, url)
            user_riders[name] = riders

        await browser.close()
        return user_riders


def export_to_csv(user_riders: dict[str, list[Rider]], filename="riders.csv"):
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Gebruiker",
                "Renner",
                "Team",
                "Uitgevallen",
                "",
                "Eind",
                "Berg",
                "Sprint",
                "Jongeren",
                "Punten",
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
                    ]
                )
    print(f"📁 CSV exported to {filename}")


if __name__ == "__main__":
    s_url = "https://www.sportpools.net/nl/giro-italia/2025/klassementen/subleague/2154"
    user_riders = asyncio.run(crawl_subleague_teamurls(subleague_url=s_url))

    for user, riders in user_riders.items():
        print(f"\n👤 {user}'s team:")
        for r in riders:
            print(f"  - {r.name} ({r.team}) → {r.points} pts")

    export_to_csv(user_riders)
