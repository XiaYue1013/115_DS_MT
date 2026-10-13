"""第 7 題：依原題使用 Google Books API，抓 Python 圖書兩頁各 10 筆。"""

from __future__ import annotations

import json
import os
from pathlib import Path

import requests

from common import OUTPUT_DIR, save_csv

URL = "https://www.googleapis.com/books/v1/volumes"
FIELDS = ["頁次", "Google圖書ID", "書名", "作者", "出版日", "出版社", "說明", "網址"]


def api_key():
    value = os.getenv("GOOGLE_BOOKS_API_KEY", "").strip()
    if not value:
        path = Path(__file__).resolve().parents[1] / ".env"
        if path.exists():
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                name, separator, setting = line.partition("=")
                if separator and name.strip().removeprefix("export ").strip() == "GOOGLE_BOOKS_API_KEY":
                    value = setting.strip().strip("\"'")
                    break
    if not value or value == "your_google_books_api_key":
        raise RuntimeError("請在專案 .env 或環境變數設定 GOOGLE_BOOKS_API_KEY。")
    return value


def fetch_page(key, start_index):
    params = {"q": "Python", "maxResults": 10, "projection": "lite", "startIndex": start_index, "key": key}
    try:
        response = requests.get(URL, params=params, timeout=30)
    except requests.RequestException:
        # requests 的例外會包含帶金鑰的完整網址，因此不顯示原始例外。
        raise RuntimeError("Google Books API 連線失敗，請確認網路後重試。") from None
    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(f"Google Books API 回傳非 JSON 資料（HTTP {response.status_code}）。") from None
    if response.status_code != 200 or "error" in data:
        message = str(data.get("error", {}).get("message", "請確認 Books API 已啟用、金鑰限制與額度。"))
        message = message.replace(key, "[已隱藏金鑰]")
        raise RuntimeError(f"Google Books API 失敗（HTTP {response.status_code}）：{message}")
    items = data.get("items", [])
    if len(items) != 10:
        raise RuntimeError(f"Google Books API startIndex={start_index} 只回傳 {len(items)} 筆，未達原題每頁 10 筆。")
    return data


def volume_row(item, page):
    info = item.get("volumeInfo", {})
    if not item.get("id") or not info.get("title"):
        raise RuntimeError("Google Books API 回傳圖書缺少 ID 或書名。")
    return {
        "頁次": page,
        "Google圖書ID": item["id"],
        "書名": info["title"],
        "作者": "、".join(info.get("authors", [])) or "API未提供",
        "出版日": info.get("publishedDate") or "API未提供",
        "出版社": info.get("publisher") or "API未提供",
        "說明": info.get("description") or "API未提供",
        "網址": info.get("infoLink") or info.get("previewLink") or item.get("selfLink", ""),
    }


def main():
    key = api_key()
    pages = [fetch_page(key, start_index) for start_index in (0, 10)]
    rows = []
    for page, response in enumerate(pages, 1):
        # 與原題相同列出真正的 API JSON；回應不包含請求金鑰。
        print(json.dumps(response, ensure_ascii=False, indent=2).replace(key, "[已隱藏金鑰]"))
        rows.extend(volume_row(item, page) for item in response["items"])
        print(f"API 第 {page} 頁完成：10 筆")
    save_csv("pythonbook.csv", rows, FIELDS)
    evidence = {"endpoint": URL, "q": "Python", "maxResults": 10, "projection": "lite",
                "startIndex": [0, 10], "pages": pages}
    (OUTPUT_DIR / "google_books_pages.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2).replace(key, "[已隱藏金鑰]"), encoding="utf-8"
    )
    # 舊版 Google Play 截圖不屬於 API 的執行證據。
    old_image = OUTPUT_DIR / "q07.png"
    if old_image.exists():
        old_image.unlink()


if __name__ == "__main__":
    main()
