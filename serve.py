#!/usr/bin/env python3
"""
Dev server for Vernacular Chums. Serves the game, and accepts photograph uploads so
you can drag pictures in from the browser instead of copying files by hand.

    python3 serve.py            then open http://localhost:8000
                                and http://localhost:8000/upload.html

Only the standard library is needed. If Pillow happens to be installed,
uploads are downscaled to 1600px and saved as JPEG, which keeps the repo
sane; without it the bytes are written through untouched.
"""
import http.server, io, json, os, re, socketserver, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
PHOTOS = os.path.join(HERE, "photos")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
MAX_BYTES = 25 * 1024 * 1024
SAFE = re.compile(r"^[A-Za-z0-9_.-]{1,120}$")

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def end_headers(self):
        # Dev server: never let the browser cache. Otherwise re-running
        # build.py appears to do nothing, because data/buildings.json is served
        # from cache and the game keeps showing the old set of buildings.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, fmt, *args):
        if self.path.startswith(("/upload", "/api")):
            super().log_message(fmt, *args)

    def _json(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/buildings":
            path = os.path.join(HERE, "data", "buildings.json")
            if not os.path.exists(path):
                return self._json(404, {"error": "run build.py first"})
            with open(path, encoding="utf-8") as f:
                return self._json(200, json.load(f))
        return super().do_GET()

    def do_PUT(self):
        """PUT /upload/<stem>.<ext> with the raw file as the body."""
        if not self.path.startswith("/upload/"):
            return self._json(404, {"error": "not found"})
        name = urllib.parse.unquote(self.path[len("/upload/"):])
        if not SAFE.match(name):
            return self._json(400, {"error": "bad filename"})
        stem, ext = os.path.splitext(name)
        if ext.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            return self._json(400, {"error": "images only"})

        length = int(self.headers.get("Content-Length", 0))
        if length <= 0 or length > MAX_BYTES:
            return self._json(413, {"error": f"size must be 1..{MAX_BYTES} bytes"})
        raw = self.rfile.read(length)

        os.makedirs(PHOTOS, exist_ok=True)
        dest = os.path.join(PHOTOS, stem + ".jpg")
        try:
            if HAVE_PIL:
                im = Image.open(io.BytesIO(raw)).convert("RGB")
                w, h = im.size
                scale = 1600 / max(w, h)
                if scale < 1:
                    im = im.resize((round(w*scale), round(h*scale)), Image.LANCZOS)
                im.save(dest, "JPEG", quality=84, optimize=True)
            else:
                dest = os.path.join(PHOTOS, name)
                with open(dest, "wb") as f:
                    f.write(raw)
        except Exception as e:
            return self._json(500, {"error": str(e)})

        rebuilt = False
        try:                                   # keep buildings.json in step
            import build
            build.main()
            rebuilt = True
        except Exception as e:
            print("rebuild failed:", e)

        return self._json(200, {"saved": os.path.basename(dest),
                                "bytes": os.path.getsize(dest),
                                "resized": HAVE_PIL, "rebuilt": rebuilt})


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    print(f"Vernacular Chums on http://localhost:{PORT}")
    print(f"Uploader     http://localhost:{PORT}/upload.html")
    if not HAVE_PIL:
        print("Pillow not installed, uploads will not be downscaled "
              "(pip3 install Pillow)")
    with Server(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")
