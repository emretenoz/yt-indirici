#!/usr/bin/env bash
# etenoz.com/ytindir -> http://ytindir.etenoz.com yönlendirmesini canlı kanka servisine ekler.
# Sunucuda root olarak çalıştırın. Tekrar çalıştırmak zararsızdır; sorun çıkarsa yedeği geri yükler.
set -euo pipefail
cd /opt/kanka

if grep -q '"/ytindir"' server.mjs; then
  echo "Yönlendirme zaten ekli."
else
  mkdir -p backups
  BACKUP="backups/server.mjs.ytindir-$(date +%Y%m%d-%H%M%S)"
  cp -p server.mjs "$BACKUP"
  echo "Yedek alındı: /opt/kanka/$BACKUP"

  python3 - <<'PY'
import re, sys
p = "server.mjs"
s = open(p, encoding="utf-8").read()
m = re.search(r'^([ \t]*)if \(pathname === "/karistir/"\) pathname', s, re.M)
if not m:
    sys.exit("HATA: eklenecek yer bulunamadı, hiçbir şey değiştirilmedi.")
ind = m.group(1)
block = (
    f'{ind}if (pathname === "/ytindir" || pathname === "/ytindir/") {{\n'
    f'{ind}  // YT İndirici kullanıcının kendi bilgisayarında çalışır; ytindir.etenoz.com DNS\'te 127.0.0.1\'e işaret eder.\n'
    f'{ind}  res.writeHead(302, {{ location: "http://ytindir.etenoz.com/", "cache-control": "no-store" }});\n'
    f'{ind}  return res.end();\n'
    f'{ind}}}\n'
)
s = s[:m.start()] + block + s[m.start():]
open(p, "w", encoding="utf-8").write(s)
print("server.mjs güncellendi.")
PY

  if ! node --check server.mjs; then
    cp -p "$BACKUP" server.mjs
    echo "HATA: kod kontrolü başarısız, yedek geri yüklendi."; exit 1
  fi

  systemctl restart kanka
  sleep 2
  if ! systemctl is-active --quiet kanka; then
    cp -p "$BACKUP" server.mjs
    systemctl restart kanka
    echo "HATA: servis başlamadı, yedek geri yüklendi."; exit 1
  fi
fi

echo "--- Kontrol:"
curl -s -o /dev/null -w "etenoz.com/       -> %{http_code}\n" https://etenoz.com/
curl -s -o /dev/null -w "etenoz.com/ytindir -> %{http_code} %{redirect_url}\n" https://etenoz.com/ytindir
