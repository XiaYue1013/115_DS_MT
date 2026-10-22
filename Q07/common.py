from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.7",
}


def save_csv(filename: str, rows: list[dict], fieldnames: list[str] | None = None):
    if not rows:
        raise RuntimeError(f"沒有資料可寫入 {filename}")
    path = OUTPUT_DIR / filename
    fields = fieldnames or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"已儲存 {len(rows)} 筆：{path}")
    return path


def new_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service

    options = webdriver.ChromeOptions()
    if os.getenv("HEADLESS", "1" if sys.platform.startswith("linux") else "0") == "1":
        options.add_argument("--headless=new")
        options.add_argument(f"user-agent={HEADERS['User-Agent']}")
    if os.getenv("CHROME_BINARY"):
        options.binary_location = os.environ["CHROME_BINARY"]
    options.add_argument("--window-size=1440,1000")
    options.add_argument("--lang=zh-TW")
    options.add_argument("--disable-blink-features=AutomationControlled")
    service = Service(executable_path=os.environ["CHROMEDRIVER"]) if os.getenv("CHROMEDRIVER") else Service()
    return webdriver.Chrome(service=service, options=options)
