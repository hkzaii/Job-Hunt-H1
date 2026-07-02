import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import os

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "Title", "Company", "Rate", "Location", "Region",
    "Platform", "Date Posted", "Job URL", "Visa Flag", "Scraped At", "Description",
]

# Extra columns appended only on specific platform tabs — never on the shared
# Job_Scrape_Log mirror tab, since other repos' scrapers also write there and
# must keep that schema stable.
EXTRA_HEADERS = {
    "Greenhouse": ["Days Since Posted"],
}


def _headers_for(worksheet_name: str) -> list:
    return HEADERS + EXTRA_HEADERS.get(worksheet_name, [])


class SheetsManager:
    def __init__(self, credentials_source: str, sheet_id: str):
        """
        credentials_source: path to credentials.json file, or raw JSON string
                            (used when injected from GitHub secret)
        """
        if os.path.isfile(credentials_source):
            creds = Credentials.from_service_account_file(credentials_source, scopes=SCOPES)
        else:
            info = json.loads(credentials_source)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)

        self.client = gspread.authorize(creds)
        self.spreadsheet = self.client.open_by_key(sheet_id)
        self._setup_sheets()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _get_or_create_worksheet(self, name: str, rows=5000, cols=20):
        try:
            return self.spreadsheet.worksheet(name)
        except gspread.WorksheetNotFound:
            return self.spreadsheet.add_worksheet(title=name, rows=rows, cols=cols)

    def _setup_sheets(self):
        ws = self._get_or_create_worksheet("Job_Scrape_Log")
        existing = ws.row_values(1)
        if existing != HEADERS:
            ws.update([HEADERS], "A1")

        err_ws = self._get_or_create_worksheet("Errors")
        err_headers = ["Timestamp", "Error Detail"]
        if err_ws.row_values(1) != err_headers:
            err_ws.update([err_headers], "A1")

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    def get_existing_urls(self, worksheet_name: str = "Job_Scrape_Log") -> set:
        ws = self._get_or_create_worksheet(worksheet_name)
        expected = _headers_for(worksheet_name)
        if ws.row_values(1) != expected:
            ws.update([expected], "A1")
        all_vals = ws.get_all_values()
        if len(all_vals) <= 1:
            return set()
        url_col = HEADERS.index("Job URL")
        return {row[url_col] for row in all_vals[1:] if len(row) > url_col and row[url_col]}

    # ------------------------------------------------------------------
    # Write jobs
    # ------------------------------------------------------------------

    def append_jobs(self, jobs: list, worksheet_name: str = "Job_Scrape_Log") -> int:
        if not jobs:
            return 0

        ws = self._get_or_create_worksheet(worksheet_name)
        existing_urls = self.get_existing_urls(worksheet_name)
        extra_cols = EXTRA_HEADERS.get(worksheet_name, [])
        url_col = HEADERS.index("Job URL")

        new_rows = []
        for job in jobs:
            url = job.get("url", "")
            if url and url in existing_urls:
                continue
            existing_urls.add(url)
            row = [
                job.get("title", ""),
                job.get("company", ""),
                job.get("rate", ""),
                job.get("location", ""),
                job.get("region", ""),
                job.get("platform", ""),
                job.get("date_posted", ""),
                url,
                job.get("visa_flag", "No"),
                job.get("scraped_at", ""),
                job.get("description", ""),
            ]
            for col in extra_cols:
                row.append(job.get(col.lower().replace(" ", "_"), ""))
            new_rows.append(row)

        if new_rows:
            ws.append_rows(new_rows, value_input_option="USER_ENTERED")
            # Mirror to main log if writing to a platform tab (trimmed back to
            # the shared 11-column schema — extra columns are tab-specific)
            if worksheet_name != "Job_Scrape_Log":
                main_ws = self._get_or_create_worksheet("Job_Scrape_Log")
                main_existing = self.get_existing_urls("Job_Scrape_Log")
                main_rows = [r[:len(HEADERS)] for r in new_rows if r[url_col] not in main_existing]
                if main_rows:
                    main_ws.append_rows(main_rows, value_input_option="USER_ENTERED")

        return len(new_rows)

    # ------------------------------------------------------------------
    # Error logging
    # ------------------------------------------------------------------

    def log_errors(self, errors: list):
        if not errors:
            return
        ws = self._get_or_create_worksheet("Errors")
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        ws.append_rows([[ts, err] for err in errors], value_input_option="USER_ENTERED")

    # ------------------------------------------------------------------
    # Read back for display
    # ------------------------------------------------------------------

    def get_recent_jobs(self, n: int = 10) -> list:
        ws = self._get_or_create_worksheet("Job_Scrape_Log")
        all_vals = ws.get_all_values()
        if len(all_vals) <= 1:
            return []
        data_rows = all_vals[1:]
        recent = data_rows[-n:] if len(data_rows) >= n else data_rows
        return [dict(zip(HEADERS, row)) for row in recent]
