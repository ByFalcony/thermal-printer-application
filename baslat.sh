#!/usr/bin/env bash
# Fiş Yazıcı başlatıcısı (Linux / macOS).
# İlk çalıştırmada proje klasöründe bir sanal ortam (.venv) kurar ve gerekli paketleri yükler.
set -e
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
    echo "Python 3 bulunamadı. Lütfen Python 3.10 veya üzerini kurun." >&2
    exit 1
fi

if ! "$PY" -c "import tkinter" >/dev/null 2>&1; then
    echo "Tkinter eksik." >&2
    echo "  Debian/Ubuntu: sudo apt install python3-tk python3-venv" >&2
    echo "  Fedora:        sudo dnf install python3-tkinter" >&2
    echo "  Arch:          sudo pacman -S tk" >&2
    echo "  macOS (Homebrew): brew install python-tk" >&2
    exit 1
fi

if [ ! -x .venv/bin/python ]; then
    echo "İlk kurulum: sanal ortam oluşturuluyor..."
    "$PY" -m venv .venv
fi

if ! .venv/bin/python -c "import bleak, PIL, customtkinter" >/dev/null 2>&1; then
    echo "Gerekli paketler yükleniyor..."
    .venv/bin/python -m pip install --upgrade pip >/dev/null
    .venv/bin/python -m pip install -r requirements.txt
fi

exec .venv/bin/python app.py "$@"
