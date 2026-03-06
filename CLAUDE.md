# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Korean search trend crawler that collects trending keywords from Google Trends (Korea) and Naver DataLab, saves results as JSON, and converts them to Markdown reports. Written in Python, designed to run continuously with 1-hour collection intervals.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the crawler (collects once immediately, then every hour)
python trend_crawler.py

# Convert collected JSON files to Markdown reports
python json_to_markdown.py                    # convert all JSON in data/
python json_to_markdown.py data/some_file.json  # convert specific file
```

## Architecture

Two standalone scripts, no shared modules:

- **`trend_crawler.py`** — Main crawler that runs in a loop. Collects data from sources:
  - Google Trends Korea via Selenium headless Chrome (primary), RSS feed via `feedparser` (fallback)
  - Naver DataLab Shopping Insight API (popular categories, popular keywords, per-category keyword rankings)
  - Naver DataLab main page HTML scraping via `BeautifulSoup` (fallback/supplement)

  Output: timestamped JSON files in `data/` (e.g., `trends_20260305_144035.json`)

- **`json_to_markdown.py`** — Converts trend JSON files into readable Markdown tables. Operates independently of the crawler.

## Data Flow

`trend_crawler.py` → `data/trends_YYYYMMDD_HHMMSS.json` → `json_to_markdown.py` → `data/trends_YYYYMMDD_HHMMSS.md`

## Key Details

- All output goes to `data/` directory (gitignored)
- Code comments and log messages are in Korean
- The JSON schema has three top-level keys: `collected_at`, `google_trends` (list), `naver_trends` (nested dict with `shopping_insight` containing `popular_categories`/`popular_keywords`/`category_keywords`, and `page_keywords`)
- The crawler uses a simple `time.sleep` loop (no scheduler library)
- Selenium + `webdriver-manager` auto-installs ChromeDriver; requires Chrome/Chromium installed on the host
