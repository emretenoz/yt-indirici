"""YT İndirici — YouTube videolarını MP3/MP4 olarak (tamamını veya bir kısmını) indiren yerel web uygulaması.

Sadece bu bilgisayarda çalışır. ayarlar.json'da alan adı (ör. indir.siten.com) tanımlıysa o adresten açılır.
Kişisel kullanım içindir.
"""
import json
import os
import re
import sys
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlsplit

BASE = Path(__file__).resolve().parent
DOWNLOADS = BASE / "indirilenler"
DOWNLOADS.mkdir(exist_ok=True)
FALLBACK_PORT = 8765


def load_settings():
    path = BASE / "ayarlar.json"
    if not path.exists():
        path.write_text(json.dumps({"alan_adi": ""}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        data = {}
    domain = str(data.get("alan_adi") or "").strip().lower()
    domain = re.sub(r"^https?://", "", domain).strip("/")
    return domain


DOMAIN = load_settings()
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "[::1]"} | ({DOMAIN} if DOMAIN else set())

# deno (YouTube'un JS doğrulaması için) sanal ortamın bin/Scripts klasöründe; PATH'e ekle.
_bin = Path(sys.executable).parent
os.environ["PATH"] = str(_bin) + os.pathsep + os.environ.get("PATH", "")

import yt_dlp  # noqa: E402
from yt_dlp.utils import download_range_func  # noqa: E402

def setup_ffmpeg():
    """imageio-ffmpeg'in getirdiği ffmpeg'i 'ffmpeg' adıyla bir klasöre kopyalar (yt-dlp bu adı arar)."""
    try:
        import shutil

        import imageio_ffmpeg

        src = Path(imageio_ffmpeg.get_ffmpeg_exe())
        dest_dir = BASE / ".ffmpeg"
        dest_dir.mkdir(exist_ok=True)
        dest = dest_dir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if not dest.exists() or dest.stat().st_size != src.stat().st_size:
            shutil.copy2(src, dest)
            dest.chmod(0o755)
        return str(dest_dir)
    except Exception:  # sistemde kurulu ffmpeg varsa onu kullanır
        return None


FFMPEG = setup_ffmpeg()
if FFMPEG:  # kısmi indirme kontrolü ffmpeg'i yalnızca PATH'te arıyor
    os.environ["PATH"] = FFMPEG + os.pathsep + os.environ["PATH"]

JOBS = {}
JOBS_LOCK = threading.Lock()


def parse_time(value):
    """'90', '1:30', '01:02:03', '1:30.5' -> saniye (float). Boşsa None."""
    value = (value or "").strip()
    if not value:
        return None
    parts = value.replace(",", ".").split(":")
    if len(parts) > 3:
        raise ValueError(f"Geçersiz zaman: {value}")
    total = 0.0
    for p in parts:
        if not re.fullmatch(r"\d+(\.\d+)?", p):
            raise ValueError(f"Geçersiz zaman: {value}")
        total = total * 60 + float(p)
    return total


def base_opts():
    opts = {"quiet": True, "no_warnings": True, "noplaylist": True, "windowsfilenames": True}
    if FFMPEG:
        opts["ffmpeg_location"] = FFMPEG
    return opts


def get_info(url):
    with yt_dlp.YoutubeDL(base_opts()) as ydl:
        info = ydl.extract_info(url, download=False)
    heights = sorted({f.get("height") for f in info.get("formats", []) if f.get("height")}, reverse=True)
    return {
        "title": info.get("title"),
        "channel": info.get("channel") or info.get("uploader"),
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "heights": heights,
    }


def update_job(job_id, **kw):
    with JOBS_LOCK:
        JOBS[job_id].update(kw)


def run_job(job_id, url, fmt, quality, start, end):
    def progress_hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            pct = (d.get("downloaded_bytes", 0) / total * 100) if total else None
            update_job(job_id, status="downloading", percent=pct, speed=d.get("_speed_str", "").strip(),
                       eta=d.get("_eta_str", "").strip())
        elif d["status"] == "finished":
            update_job(job_id, status="processing", percent=100)

    def pp_hook(d):
        if d["status"] == "started":
            update_job(job_id, status="processing")

    opts = base_opts()
    opts.update({
        "outtmpl": str(DOWNLOADS / f"%(title).80s-{job_id}.%(ext)s"),
        "progress_hooks": [progress_hook],
        "postprocessor_hooks": [pp_hook],
    })

    if fmt == "mp3":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
                                   "preferredquality": str(quality or "192")}]
    else:
        h = f"[height<={int(quality)}]" if quality and str(quality).isdigit() else ""
        # Önce mp4 uyumlu (h264/aac) akışlar, yoksa en iyisi; sonuç her durumda mp4.
        opts["format"] = (f"bv*{h}[vcodec^=avc1]+ba[ext=m4a]/bv*{h}[ext=mp4]+ba[ext=m4a]/"
                          f"bv*{h}+ba/b{h}/b")
        opts["merge_output_format"] = "mp4"
        opts["postprocessors"] = [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}]

    if start is not None or end is not None:
        opts["download_ranges"] = download_range_func(None, [(start or 0, end if end is not None else float("inf"))])
        opts["force_keyframes_at_cuts"] = True  # kesimin tam istenen saniyeden olması için

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        files = sorted(DOWNLOADS.glob(f"*-{job_id}.*"), key=lambda p: p.stat().st_mtime, reverse=True)
        files = [f for f in files if f.suffix.lower() in (".mp3", ".mp4")] or files
        if not files:
            raise RuntimeError("Dosya oluşturulamadı.")
        f = files[0]
        nice = f.name.replace(f"-{job_id}", "")
        update_job(job_id, status="done", percent=100, file=f.name, filename=nice)
    except Exception as e:  # noqa: BLE001
        msg = re.sub(r"\x1b\[[0-9;]*m", "", str(e)).replace("ERROR: ", "")
        update_job(job_id, status="error", error=msg)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def allowed(self):
        """Sadece bu bilgisayardan ve bilinen adreslerden gelen isteklere izin ver."""
        if self.client_address[0] not in ("127.0.0.1", "::1", "::ffff:127.0.0.1"):
            return False
        host = (self.headers.get("Host") or "").lower()
        host = host.rsplit(":", 1)[0] if not host.startswith("[") else host.split("]")[0] + "]"
        return host in ALLOWED_HOSTS

    def same_origin_json(self):
        """POST isteği gerçekten bizim sayfamızdan mı geliyor? (CSRF koruması)

        Başka bir site, tarayıcı üzerinden 127.0.0.1'e "basit" bir POST gönderebilir. Host başlığı o zaman
        da 127.0.0.1 olduğu için allowed() bunu durdurmaz. Bu yüzden ayrıca bakıyoruz:
        - Origin başlığı (tarayıcı her POST'ta ekler, sayfa değiştiremez) bizim adreslerimizden biri olmalı.
        - Content-Type application/json olmalı. Başka bir site bunu ancak tarayıcının önce izin sorduğu
          (preflight/OPTIONS) bir istekle gönderebilir; biz OPTIONS'a izin vermediğimiz için istek hiç gelmez.
        """
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            return False
        origin = self.headers.get("Origin")
        if origin is None:  # tarayıcı dışı araçlar (curl vb.) Origin göndermez; zaten yalnızca bu bilgisayardan
            return True
        host = urlsplit(origin).hostname or ""
        return host in ALLOWED_HOSTS or f"[{host}]" in ALLOWED_HOSTS

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (ConnectionError, BrokenPipeError):
            pass

    def parse_request(self):
        ok = super().parse_request()
        if ok and not self.allowed():
            self.send_error(403, "Forbidden")
            return False
        return ok

    def do_GET(self):
        if self.path == "/api/ping":
            return self.send_json({"app": "yt-indirici"})
        if self.path in ("/", "/index.html"):
            body = (BASE / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path.startswith("/api/job/"):
            job_id = self.path.rsplit("/", 1)[-1]
            with JOBS_LOCK:
                job = dict(JOBS.get(job_id) or {})
            self.send_json(job or {"status": "error", "error": "İş bulunamadı"}, 200 if job else 404)
        elif self.path.startswith("/file/"):
            job_id = self.path.rsplit("/", 1)[-1]
            with JOBS_LOCK:
                job = dict(JOBS.get(job_id) or {})
            path = DOWNLOADS / job.get("file", "") if job.get("file") else None
            if not path or not path.is_file():
                return self.send_json({"error": "Dosya yok"}, 404)
            ctype = "audio/mpeg" if path.suffix == ".mp3" else "video/mp4"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(path.stat().st_size))
            self.send_header("Content-Disposition",
                             f"attachment; filename=\"download{path.suffix}\"; filename*=UTF-8''{quote(job['filename'])}")
            self.end_headers()
            with open(path, "rb") as fh:
                while chunk := fh.read(1 << 20):
                    self.wfile.write(chunk)
        else:
            self.send_json({"error": "Bulunamadı"}, 404)

    def do_POST(self):
        if not self.same_origin_json():
            return self.send_json({"error": "İzin verilmeyen istek"}, 403)
        try:
            data = self.read_json()
            if self.path == "/api/quit":
                self.send_json({"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            url = (data.get("url") or "").strip()
            if not url:
                return self.send_json({"error": "Bağlantı boş"}, 400)
            if self.path == "/api/info":
                return self.send_json(get_info(url))
            if self.path == "/api/download":
                fmt = "mp3" if data.get("format") == "mp3" else "mp4"
                start, end = parse_time(data.get("start")), parse_time(data.get("end"))
                if start is not None and end is not None and end <= start:
                    return self.send_json({"error": "Bitiş zamanı başlangıçtan sonra olmalı"}, 400)
                job_id = uuid.uuid4().hex[:8]
                with JOBS_LOCK:
                    JOBS[job_id] = {"status": "starting", "percent": 0, "created": time.time()}
                threading.Thread(target=run_job, daemon=True,
                                 args=(job_id, url, fmt, data.get("quality"), start, end)).start()
                return self.send_json({"job": job_id})
            self.send_json({"error": "Bulunamadı"}, 404)
        except ValueError as e:
            self.send_json({"error": str(e)}, 400)
        except Exception as e:  # noqa: BLE001
            msg = re.sub(r"\x1b\[[0-9;]*m", "", str(e)).replace("ERROR: ", "")
            self.send_json({"error": msg}, 500)


def make_url(port):
    host = DOMAIN or "127.0.0.1"
    return f"http://{host}" + ("" if port == 80 else f":{port}")


def already_running():
    """Uygulama zaten açıksa adresini döndürür."""
    import urllib.request

    for port in (80, FALLBACK_PORT):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=1) as r:
                if json.load(r).get("app") == "yt-indirici":
                    return make_url(port)
        except Exception:  # noqa: BLE001
            pass
    return None


def bind_server():
    if os.environ.get("PORT"):
        candidates = [("127.0.0.1", int(os.environ["PORT"]))]
    elif DOMAIN:
        # 80 portu: adresin sonuna port yazmaya gerek kalmaz. macOS'ta normal kullanıcı 80'i yalnızca
        # 0.0.0.0'da açabiliyor; dışarıdan gelen istekler zaten Handler.allowed() ile reddediliyor.
        candidates = [("127.0.0.1", 80), ("0.0.0.0", 80), ("127.0.0.1", FALLBACK_PORT)]
    else:
        candidates = [("127.0.0.1", FALLBACK_PORT)]
    for addr in candidates:
        try:
            return ThreadingHTTPServer(addr, Handler)
        except OSError:
            continue
    return None


def main():
    running = already_running()
    server = None if running else bind_server()
    if server is None:
        if running and not os.environ.get("NO_BROWSER"):
            webbrowser.open(running)
        if not running:
            print("Uygun bir port açılamadı.")
        return
    url = make_url(server.server_address[1])
    print(f"YT İndirici çalışıyor: {url}")
    print(f"Dosyalar ayrıca buraya kaydedilir: {DOWNLOADS}")
    print("Kapatmak için sayfadaki 'Uygulamayı kapat' düğmesini kullanın (veya Ctrl+C).")
    if not os.environ.get("NO_BROWSER"):
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
