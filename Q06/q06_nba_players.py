"""第 6 題：抓 CLE、HOU、GSW 最新指定球季的球員名冊。"""

import os
import time
from bs4 import BeautifulSoup

from common import get, save_csv

YEAR = os.getenv("NBA_YEAR", "2026")
TEAMS = ["CLE", "HOU", "GSW"]
STATS = {
    "number": "背號",
    "player": "姓名",
    "pos": "位置",
    "weight": "體重",
    "birth_date": "生日",
    "years_experience": "經驗",
    "college": "大學",
}


def main():
    rows = []
    for team in TEAMS:
        url = f"https://www.basketball-reference.com/teams/{team}/{YEAR}.html"
        response = get(url)
        soup = BeautifulSoup(response.text, "lxml")
        table = soup.select_one("table#roster")
        if not table:
            raise RuntimeError(f"找不到 {team} {YEAR} 的 roster 表格：{url}")
        for tr in table.select("tbody tr"):
            row = {"球隊": team}
            for stat, label in STATS.items():
                cell = tr.select_one(f"[data-stat='{stat}']")
                row[label] = cell.get_text(" ", strip=True) if cell else ""
            if row["姓名"]:
                rows.append(row)
        print(f"完成 {team}：{len([r for r in rows if r['球隊'] == team])} 位")
        time.sleep(3)
    save_csv("players.csv", rows, ["球隊", *STATS.values()])


if __name__ == "__main__":
    main()
