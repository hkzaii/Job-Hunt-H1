import asyncio
import json
import os
import re
import time
from datetime import datetime

import aiohttp
import requests as req
from dotenv import load_dotenv

from utils import (
    SEARCH_KEYWORDS, get_random_user_agent, should_exclude,
    detect_region, is_remote_job, extract_rate, core_term,
)
from sheets import SheetsManager

load_dotenv()

SHEET_ID      = os.getenv("SHEET_ID")
CREDS         = os.getenv("GOOGLE_CREDENTIALS", "credentials.json")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK", "")
CONCURRENCY   = int(os.getenv("CONCURRENCY", "20"))
COMPANIES_FILE = "companies.json"
PLATFORM_NAME = "Greenhouse"


def _send_slack(message: str):
    if not SLACK_WEBHOOK:
        return
    try:
        req.post(SLACK_WEBHOOK, json={"text": message}, timeout=10)
    except Exception:
        pass


def build_job(title, company, rate, location, url, date_posted, description=""):
    full_text = f"{title} {location} {description}"
    excluded, _ = should_exclude(full_text)
    region = detect_region(location, description)
    remote = is_remote_job(location, description)
    return {
        "title": (title or "").strip() or "N/A",
        "company": (company or "").strip() or "N/A",
        "rate": (rate or "").strip() or "Not specified",
        "location": (location or "").strip() or "Remote",
        "region": region,
        "platform": PLATFORM_NAME,
        "date_posted": (date_posted or "").strip() or "N/A",
        "url": (url or "").strip(),
        "visa_flag": "Yes" if excluded else "No",
        "scraped_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "description": (description or "").strip()[:2000],
        "_excluded": excluded,
        "_is_remote": remote,
    }


async def fetch_company(session, sem, slug):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    async with sem:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status != 200:
                    return slug, []
                data = await r.json(content_type=None)
                return slug, data.get("jobs", [])
        except Exception:
            return slug, []


async def fetch_all_companies(companies: list) -> dict:
    sem = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY)
    headers = {"User-Agent": get_random_user_agent(), "Accept": "application/json"}
    results = {}
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        tasks = [asyncio.create_task(fetch_company(session, sem, slug)) for slug in companies]
        done = 0
        for coro in asyncio.as_completed(tasks):
            slug, jobs = await coro
            if jobs:
                results[slug] = jobs
            done += 1
            if done % 1000 == 0:
                print(f"  ...{done}/{len(companies)} companies checked "
                      f"({len(results)} active boards found so far)")
    return results


def match_jobs(company_jobs: dict) -> list:
    cores = sorted(set(core_term(k) for k in SEARCH_KEYWORDS))
    matched = []
    for slug, jobs in company_jobs.items():
        company_name = slug.replace("-", " ").replace("_", " ").title()
        for item in jobs:
            title = item.get("title", "") or ""
            title_lower = title.lower()
            if not any(re.search(rf"\b{re.escape(core)}\b", title_lower) for core in cores):
                continue

            offices = item.get("offices") or []
            location = ", ".join(o["name"] for o in offices if o.get("name")) or "Remote"
            url = item.get("absolute_url", "")
            date_posted = (item.get("updated_at") or "")[:10]
            desc = re.sub(r"<[^>]+>", " ", item.get("content") or "")

            job = build_job(
                title=title,
                company=company_name,
                rate=extract_rate(desc),
                location=location,
                url=url,
                date_posted=date_posted,
                description=desc,
            )
            if job["_is_remote"] and not job["_excluded"]:
                matched.append(job)
    return matched


async def main():
    if not SHEET_ID:
        raise ValueError("SHEET_ID is not set in .env")

    with open(COMPANIES_FILE) as f:
        companies = json.load(f)

    print("=" * 60)
    print("Greenhouse Full-Lookup Scraper Starting")
    print(f"Companies to check : {len(companies)}")
    print(f"Keywords           : {len(SEARCH_KEYWORDS)}")
    print(f"Concurrency        : {CONCURRENCY}")
    print("=" * 60)

    start = time.time()
    sheets = SheetsManager(credentials_source=CREDS, sheet_id=SHEET_ID)

    company_jobs = await fetch_all_companies(companies)
    fetch_elapsed = time.time() - start
    live_boards = len(company_jobs)
    print(f"\nFetch complete in {fetch_elapsed:.1f}s — "
          f"{live_boards}/{len(companies)} companies have active boards")

    valid_jobs = match_jobs(company_jobs)
    print(f"Matched {len(valid_jobs)} valid jobs against your keywords")

    new_count = sheets.append_jobs(valid_jobs, worksheet_name="Greenhouse")
    total_elapsed = time.time() - start

    print("\n" + "=" * 60)
    print(f"Total valid  : {len(valid_jobs)}")
    print(f"New added    : {new_count}")
    print(f"Duplicates   : {len(valid_jobs) - new_count}")
    print(f"Runtime      : {total_elapsed:.1f}s")
    print("=" * 60)

    slack_msg = (
        f"*Greenhouse Full-Lookup Run Complete* ✅\n"
        f"• Companies checked: {len(companies)} ({live_boards} active)\n"
        f"• Valid jobs found: {len(valid_jobs)}\n"
        f"• New jobs added: {new_count}\n"
        f"• Runtime: {total_elapsed / 60:.1f} min"
    )
    _send_slack(slack_msg)

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
