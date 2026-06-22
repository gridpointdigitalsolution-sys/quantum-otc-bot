# TOOLS INSTALLED — Options Bot project (recorded 2026-06-20)

Authentic inventory of scraping/data tools available on this machine. Python 3.14.4.

## yt-dlp (v2026.06.09+)
- **What:** downloads YouTube video subtitles/captions (+ media if wanted).
- **Use here:** the transcript scraping of all 29 channels (binary + forex). THE correct tool
  for YouTube. Install: `python -m pip install yt-dlp`.
- **Limit:** YouTube rate-limits bulk pulls by IP — gentle delays + `--download-archive`
  (skip done, fetch only missing). No tool bypasses the rate-limit; patience is the only fix.
- **NEVER parallelize downloads** (more requests = harder throttle/IP ban).

## ScrapeGraphAI (v2.1.3) — installed 2026-06-20
- **What:** LLM-powered WEBSITE scraper. Reads HTML pages, extracts STRUCTURED data from a
  plain-English prompt. Repo: https://github.com/ScrapeGraphAI/Scrapegraph-ai
- **Needs:** an LLM API key (OpenAI key already on file) + `playwright install` for JS pages.
- **Does NOT help with YouTube subtitles** — wrong tool for that (yt-dlp owns that job).
- **Real uses for THIS project (later, building the bot's web-data sources):**
  1. Scrape broker OTC asset lists + live payout % (Deriv/PO/Quotex pages) -> clean table
     (feeds the payout-gate scanner + dashboard).
  2. Economic calendar / news sites -> event times for a news-blackout filter.
  3. Broker review/trust pages -> structured data instead of manual reading.
- **Honest status:** nice-to-have for live web data when building; NOT core, NOT a speed-up
  for the current transcript work.

## PyMuPDF (fitz)
- **What:** PDF text extraction. Used to digest the 16 trading books -> KB1-KB9.
