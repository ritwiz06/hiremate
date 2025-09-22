import json, re, time, sqlite3
from pathlib import Path
from urllib.parse import urlencode
from datetime import datetime
from playwright.sync_api import sync_playwright

# Project paths (DB relative to db/ folder) [web:171]
ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "jobs.db"
# Cookies exported from a logged-in browser session (safer than storing passwords) [web:171]
COOKIES_PATH = Path(__file__).with_name("cookies.json")

# Define a few base searches; you can expand this list or load from a JSON config later [web:171]
SEARCH_QUERIES = [
  {"keywords": "Software Engineer", "location": "United States"},
  {"keywords": "Data Scientist", "location": "United States"},
  {"keywords": "Machine Learning Engineer", "location": "United States"},
]

# Limit pages to avoid aggressive scraping; tune up/down as needed [web:171]
MAX_PAGES = 5
# Small delay between actions to reduce bot detection and ensure content renders [web:171]
SCROLL_DELAY = 0.8

def build_search_url(keywords: str, location: str, page: int = 0) -> str:
  """
  Construct a LinkedIn Jobs search URL for the given keywords/location and a page number. [web:171]
  """
  params = {"keywords": keywords, "location": location, "position": 1, "pageNum": page}
  return f"https://www.linkedin.com/jobs/search?{urlencode(params)}"

def extract_job_id(url: str) -> str | None:
  """
  Extract LinkedIn job ID from a job URL, e.g., /jobs/view/1234567890/ -> 1234567890. [web:171]
  """
  m = re.search(r"/jobs/view/(\d+)", url)
  return m.group(1) if m else None

def insert_job(conn, rec):
  """
  Insert one job into the jobs table; INSERT OR IGNORE deduplicates based on job_id. [web:166]
  """
  conn.execute("""
    INSERT OR IGNORE INTO jobs(job_id, title, company, location, url, description, date_posted)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  """, (rec.get("job_id"), rec.get("title"), rec.get("company"),
        rec.get("location"), rec.get("url"), rec.get("description"),
        rec.get("date_posted")))

def scrape():
  """
  Main scraping routine:
  - Loads session cookies to reuse authenticated session (no passwords) [web:171]
  - Opens LinkedIn job search pages, iterates job cards, and extracts fields [web:171][web:159]
  - Writes rows into SQLite; FTS triggers keep the index in sync automatically [web:166]
  """
  with sqlite3.connect(DB_PATH) as conn, sync_playwright() as p:
    # Launch Chromium headless for speed; set headless=False during debugging to see UI [web:171]
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()

    # Load cookies from file if provided (must be valid for linkedin.com domain) [web:171]
    if COOKIES_PATH.exists():
      cookies = json.load(open(COOKIES_PATH, "r", encoding="utf-8"))
      context.add_cookies(cookies)

    page = context.new_page()

    total = 0
    for q in SEARCH_QUERIES:
      # Iterate several "pages" by tweaking the pageNum parameter to load more results [web:171]
      for page_num in range(MAX_PAGES):
        url = build_search_url(q["keywords"], q["location"], page_num)
        # networkidle waits until network activity is low, useful on dynamic sites [web:171]
        page.goto(url, timeout=60000, wait_until="networkidle")
        time.sleep(1.0)  # small buffer for layout/JS hydrate [web:171]

        # Left column list of job cards; selector may evolve—adjust as LinkedIn DOM changes [web:159]
        job_cards = page.locator("ul.scaffold-layout__list-container li")
        count = job_cards.count()
        if count == 0:
          # No jobs found for this page; go to next query [web:171]
          break

        # Cap per page to avoid scraping too aggressively and reduce run time [web:171]
        for idx in range(min(count, 25)):
          # Click each card to load details in the right pane [web:171]
          job_cards.nth(idx).click()
          page.wait_for_timeout(int(SCROLL_DELAY * 1000))

          # Extract fields; use .first to avoid errors if multiple nodes match [web:171]
          title = (page.locator("h2.top-card-layout__title").first.text_content() or "").strip()
          company = (page.locator("a.topcard__org-name-link, span.topcard__flavor").first.text_content() or "").strip()
          location = (page.locator("span.topcard__flavor--bullet").first.text_content() or "").strip()
          desc = (page.locator("div.show-more-less-html__markup").first.text_content() or "").strip()
          job_url = page.url
          job_id = extract_job_id(job_url)
          date_text = (page.locator("span.posted-time-ago__text").first.text_content() or "").strip()

          # Build record with all relevant fields for downstream matching [web:171]
          rec = {
            "job_id": job_id,
            "title": title,
            "company": company,
            "location": location,
            "url": job_url,
            "description": desc,
            "date_posted": date_text
          }
          # Insert into DB; triggers auto-update FTS index [web:166]
          insert_job(conn, rec)
          total += 1

    # Commit all inserts and close the browser context cleanly [web:166]
    conn.commit()
    page.close(); context.close(); browser.close()
    print(f"Inserted/checked {total} postings at {datetime.utcnow().isoformat()}Z")

if __name__ == "__main__":
  scrape()
