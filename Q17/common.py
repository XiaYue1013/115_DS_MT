from __future__ import annotations

import csv
import os
from pathlib import Path
import tempfile

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


def new_driver(profile_dir=None):
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service

    options = webdriver.ChromeOptions()
    cached_driver = None
    if os.getenv("HEADLESS") == "1":
        options.add_argument("--headless=new")
        options.add_argument(f"user-agent={HEADERS['User-Agent']}")
    if os.getenv("CHROME_NO_SANDBOX") == "1":
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
    if os.getenv("CHROME_BINARY"):
        options.binary_location = os.environ["CHROME_BINARY"]
    else:
        # 本機檢查下載的 Chrome for Testing 可直接重用，不必手動指定路徑。
        cache = Path(tempfile.gettempdir()) / "midterm-selenium-cache"
        browsers = sorted(cache.glob("chrome/*/*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"))
        if browsers:
            binary = browsers[-1]
            options.binary_location = str(binary)
            version = binary.parents[3].name
            platform = binary.parents[4].name
            cached_driver = cache / "chromedriver" / platform / version / "chromedriver"
        else:
            cached_driver = None
            # Selenium Manager 會準備穩定版瀏覽器及對應驅動。
            options.browser_version = "stable"
    if profile_dir is not None:
        profile_dir = Path(profile_dir).resolve()
        profile_dir.mkdir(parents=True, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--window-size=1440,1000")
    options.add_argument("--lang=zh-TW")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver_path = os.getenv("CHROMEDRIVER") or (str(cached_driver) if not os.getenv("CHROME_BINARY") and cached_driver and cached_driver.exists() else None)
    service = Service(executable_path=driver_path) if driver_path else Service()
    return webdriver.Chrome(service=service, options=options)
