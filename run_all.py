"""依序執行 Q01–Q17，結束時列出每題結果。可用 `python run_all.py 1 5 17` 只跑指定題號。"""
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TIMEOUT = 600

env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
env.setdefault("HEADLESS", "1")

wanted = {int(a) for a in sys.argv[1:]} or set(range(1, 18))
results = []
for script in sorted(ROOT.glob("Q[0-9][0-9]/q[0-9][0-9]_*.py")):
    number = int(script.parent.name[1:])
    if number not in wanted:
        continue
    print(f"\n===== {script.parent.name} {script.name} =====", flush=True)
    start = time.time()
    try:
        code = subprocess.run([sys.executable, str(script)], cwd=ROOT, env=env, timeout=TIMEOUT).returncode
    except subprocess.TimeoutExpired:
        code = "逾時"
    results.append((script.parent.name, code, time.time() - start))

print("\n===== 執行結果 =====")
for name, code, seconds in results:
    print(f"{name}  {'成功' if code == 0 else '失敗(' + str(code) + ')'}  {seconds:.0f}s")
failed = [n for n, c, _ in results if c != 0]
print(f"\n成功 {len(results) - len(failed)} / {len(results)} 題" + (f"；失敗：{', '.join(failed)}" if failed else ""))
print("輸出位置：各題資料夾下的 output/")
sys.exit(1 if failed else 0)
