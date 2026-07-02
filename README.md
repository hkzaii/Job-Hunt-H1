# Job Hunt H1

Greenhouse ATS job scraper. Checks ~8,300 companies' public Greenhouse job boards
for roles matching a keyword list, filters for remote-only and excludes visa-sponsorship
listings, then writes matches to a shared Google Sheet.

Runs daily via GitHub Actions (`.github/workflows/scraper.yml`).

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in your Sheet ID
3. Place your Google service account `credentials.json` in this folder
4. `python main.py`
