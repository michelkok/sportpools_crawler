# 🧗‍♂️ Sportpools Team Crawler

This project logs into [sportpools.net](https://www.sportpools.net), navigates to a specific subleague, extracts all user teams, and compiles detailed rider information for each team — including GC points, sprint points, and whether the rider has DNF'd. The results are exported to a CSV file.

## Features

- Headless login using Playwright
- Rider data extraction with BeautifulSoup
- Automatically detects:
  - Rider name
  - Team
  - DNF status
  - Cost
  - GC, mountain, sprint, young GC, and total points
- CSV export for further analysis

## Setup

This project is designed to be run in a **VS Code devcontainer** with Python 3.12. It uses [uv](https://github.com/astral-sh/uv) for fast dependency management.

1. Clone the repository and open it in a devcontainer (VS Code will prompt you to reopen).

2. Set your login credentials:
   Create a `.env` file in the project root:

   ```
   USERNAME=your_email@example.com
   PASSWORD=yourpassword
   ```

   You can use a disposable email from [10minutemail.com](https://10minutemail.com) to register an account on sportpools.net without exposing your real email. Any account will allow access to all subleagues.

3. Run the crawler:

   ```bash
   /workspace/.venv/bin/python /workspace/sportpools_crawler/crawler.py
   ```

   This will:
   - Log in
   - Visit the subleague
   - Extract all team URLs and crawl rider data
   - Export everything to `riders.csv`

## Output

The CSV file contains the following columns:

- `user`: the user's name
- `rider`: rider's name
- `team`: professional cycling team
- `dnf`: whether the rider did not finish (True/False)
- `cost`: rider's cost in the game
- `gc_points`: general classification points
- `mountain_points`: mountain classification points
- `sprint_points`: sprint classification points
- `young_gc_points`: young rider classification points
- `points`: total points

## Dependencies

Managed automatically in the devcontainer using `uv`.

## Notes

- Scraping is read-only and mimics a logged-in user session.
- Project can easily be extended to scrape other competitions or run periodically.

## License

MIT — Free to use, modify, or build upon.
