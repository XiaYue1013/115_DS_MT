#!/usr/bin/env bash
# macOS / Linux：建立虛擬環境、安裝套件並一次跑完 Q01–Q17。用法：./run_all.sh [題號...]
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
VENV=.venv
# 若 .venv 是別的作業系統建立的（無法執行），改用 .venv-unix
if [ -d "$VENV" ] && ! "$VENV/bin/python" -c "" >/dev/null 2>&1; then VENV=.venv-unix; fi
[ -x "$VENV/bin/python" ] || "$PY" -m venv "$VENV"
"$VENV/bin/python" -m pip install -q -r requirements.txt
[ -f .env ] || cp .env.example .env
"$VENV/bin/python" run_all.py "$@"
