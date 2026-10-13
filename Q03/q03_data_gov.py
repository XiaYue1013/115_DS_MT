"""第 3 題：由 data.gov.tw 官方 API 找到腸病毒資料的最新 CSV 並下載。"""

import ssl
import subprocess
from pathlib import Path
import certifi

from common import OUTPUT_DIR, get

META_URL = "https://data.gov.tw/api/v2/rest/dataset/14590"
TWCA_INTERMEDIATE = "https://sslserver.twca.com.tw/cacert/Cyber_SSL_2023.crt"


def twca_ca_bundle():
    """補上疾管署伺服器目前未送出的 TWCA 中繼憑證，仍維持 TLS 驗證。"""
    # Python 3.13 的嚴格驗證會拒絕 TWCA 下載站的一個舊式憑證欄位；
    # 由系統 curl 先做 TLS 驗證並取得官方中繼憑證，再交回 requests 使用。
    der = subprocess.run(
        ["curl", "--fail", "--silent", "--show-error", "--location", TWCA_INTERMEDIATE],
        check=True,
        capture_output=True,
    ).stdout
    pem = ssl.DER_cert_to_PEM_cert(der)
    path = OUTPUT_DIR / "twca_ca_bundle.pem"
    path.write_text(Path(certifi.where()).read_text(encoding="ascii") + pem, encoding="ascii")
    return path


def main():
    metadata = get(META_URL).json()["result"]
    resource = next(
        item
        for item in metadata["distribution"]
        if item.get("resourceFormat", "").upper() == "CSV"
    )
    csv_response = get(resource["resourceDownloadUrl"], verify=str(twca_ca_bundle()))
    path = OUTPUT_DIR / "NHI_EnteroviralInfection.csv"
    path.write_bytes(csv_response.content)
    print("資料集：", metadata["title"])
    print("更新時間：", metadata["modifiedDate"])
    print("下載網址：", resource["resourceDownloadUrl"])
    print("已儲存：", path)


if __name__ == "__main__":
    main()
