"""第 3 題：由官方 API 下載腸病毒 CSV；站台異常時明確標示使用既有資料。"""

import csv
from datetime import datetime
import io
from pathlib import Path
import ssl
import subprocess
import tempfile
import time

import certifi
import requests

from common import HEADERS, OUTPUT_DIR, get

META_URL = "https://data.gov.tw/api/v2/rest/dataset/14590"
TWCA_INTERMEDIATE = "https://sslserver.twca.com.tw/cacert/Cyber_SSL_2023.crt"
FIELDS = ["年", "週", "就診類別", "年齡別", "縣市", "腸病毒健保就診人次", "健保就診總人次", "縣市別代碼"]


def twca_ca_bundle():
    """只在系統信任庫驗證失敗時補入官方中繼憑證，仍維持 TLS 驗證。"""
    der = subprocess.run(
        ["curl", "--fail", "--silent", "--show-error", "--location",
         "--connect-timeout", "10", "--max-time", "30", TWCA_INTERMEDIATE],
        check=True, capture_output=True, timeout=35,
    ).stdout
    pem = ssl.DER_cert_to_PEM_cert(der)
    path = OUTPUT_DIR / "twca_ca_bundle.pem"
    path.write_text(Path(certifi.where()).read_text(encoding="ascii") + pem, encoding="ascii")
    return path


def validate_csv(content):
    """避免將錯誤頁、空檔或欄位不完整的資料當作下載結果。"""
    rows = csv.reader(io.StringIO(content.decode("utf-8-sig")), strict=True)
    if next(rows, None) != FIELDS:
        raise ValueError("CSV 欄位與官方資料集不符")
    count = 0
    for row in rows:
        if len(row) != len(FIELDS):
            raise ValueError("CSV 資料列不完整")
        count += 1
    if not count:
        raise ValueError("CSV 沒有資料列")
    return count


def download_csv(url):
    verify = True
    for attempt in range(1, 3):
        print(f"下載 CSV（第 {attempt}/2 次）…", flush=True)
        try:
            try:
                response = requests.get(url, headers=HEADERS, timeout=(10, 60), verify=verify)
            except requests.exceptions.SSLError:
                verify = str(twca_ca_bundle())
                response = requests.get(url, headers=HEADERS, timeout=(10, 60), verify=verify)
            response.raise_for_status()
            validate_csv(response.content)
            return response.content
        except requests.RequestException:
            if attempt == 2:
                raise
            print("連線失敗，2 秒後重試。", flush=True)
            time.sleep(2)


def use_existing(path, error):
    if not path.is_file():
        print(f"下載失敗：{error}")
        print("沒有可用的既有 CSV。請稍後重試，或換網路後再執行。")
        return False
    try:
        count = validate_csv(path.read_bytes())
    except (OSError, ValueError, csv.Error) as exc:
        print(f"下載失敗：{error}\n既有 CSV 也無法使用：{exc}")
        return False
    modified = datetime.fromtimestamp(path.stat().st_mtime).isoformat(sep=" ", timespec="seconds")
    print(f"警告：本次未取得最新資料（{error}）。")
    print(f"使用既有檔案：{path}")
    print(f"檔案修改時間：{modified}；資料列數：{count}。此時間不代表官方更新時間。")
    return True


def main():
    path = OUTPUT_DIR / "NHI_EnteroviralInfection.csv"
    try:
        metadata = get(META_URL).json()["result"]
        resource = next(
            (item for item in metadata["distribution"]
             if item.get("resourceFormat", "").upper() == "CSV"), None,
        )
        if resource is None:
            raise ValueError("官方資料集未提供 CSV 下載網址")
        url = resource["resourceDownloadUrl"]
        print("資料集：", metadata["title"], flush=True)
        print("下載網址：", url, flush=True)
        content = download_csv(url)
    except (requests.RequestException, ValueError, KeyError, csv.Error,
            OSError, subprocess.SubprocessError) as exc:
        return 0 if use_existing(path, exc) else 1

    # 下載與格式檢查完成後才替換，避免下載失敗破壞既有資料。
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=OUTPUT_DIR, suffix=".tmp", delete=False) as file:
            temporary = Path(file.name)
            file.write(content)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print("下載成功；資料集更新時間：", metadata["modifiedDate"])
    print("已儲存：", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
