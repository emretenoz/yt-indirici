#!/bin/bash
# Ortak Mac çalıştırıcı: gerekirse kurar, bileşenleri günceller, uygulamayı başlatır.
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  echo "İlk kurulum: uv yükleniyor (Python yöneticisi)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh || { echo "uv kurulamadı."; exit 1; }
  export PATH="$HOME/.local/bin:$PATH"
fi
[ -x .venv/bin/python ] || uv venv --python 3.12 .venv
echo "Bileşenler güncelleniyor..."
uv pip install -q --python .venv -U -r requirements.txt || echo "Güncelleme atlandı (internet yok olabilir)."
exec .venv/bin/python app.py
