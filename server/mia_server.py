#!/usr/bin/env python3
"""Mia's 1st Birthday — photo drop server (runs on the Pi, public via Tailscale funnel).
Endpoints:
  POST /upload            raw JPEG body, headers: X-Guest (name), X-Party (token)
  GET  /list?pin=0000     JSON list of photos
  GET  /photos/<file>?pin=0000
  GET  /zip?pin=0000      all photos as one zip
  GET  /health
Photos land in ../photos/ — never leaves the Pi unless the mother downloads.
"""
import http.server, json, os, re, time, zipfile, io, socketserver

BASE = os.path.dirname(os.path.abspath(__file__))
PHOTOS = os.path.join(BASE, '..', 'photos')
PIN = '0000'
PARTY = 'mia2026'          # embedded in the app; stops random internet uploads
MAX_BYTES = 8 * 1024 * 1024
os.makedirs(PHOTOS, exist_ok=True)

class H(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Guest, X-Party')

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def _deny(self, code=403, msg='no'):
        self.send_response(code); self._cors()
        self.send_header('Content-Type', 'application/json'); self.end_headers()
        self.wfile.write(json.dumps({'error': msg}).encode())

    def _pin_ok(self):
        return ('pin=' + PIN) in (self.path.split('?', 1) + [''])[1]

    def do_POST(self):
        if self.path.split('?', 1)[0] == '/zipsel':
            if not self._pin_ok():
                return self._deny(403, 'pin')
            n = int(self.headers.get('Content-Length', 0))
            if not (0 < n <= 200000):
                return self._deny(413, 'too big')
            try:
                names = json.loads(self.rfile.read(n)).get('names', [])[:2000]
            except Exception:
                return self._deny(400, 'bad json')
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, 'w', zipfile.ZIP_STORED) as z:
                for f in names:
                    f = re.sub(r'[^A-Za-z0-9_.-]', '', str(f))
                    fp = os.path.join(PHOTOS, f)
                    if f.endswith('.jpg') and os.path.isfile(fp):
                        z.write(fp, f)
            b = buf.getvalue()
            self.send_response(200); self._cors()
            self.send_header('Content-Type', 'application/zip')
            self.send_header('Content-Disposition', 'attachment; filename="mia-selected.zip"')
            self.send_header('Content-Length', str(len(b)))
            self.end_headers()
            self.wfile.write(b); return
        if self.path.split('?', 1)[0] == '/subscribe':
            n = int(self.headers.get('Content-Length', 0))
            if not (0 < n <= 8000):
                return self._deny(413, 'too big')
            try:
                sub = json.loads(self.rfile.read(n))
                assert 'endpoint' in sub
            except Exception:
                return self._deny(400, 'bad sub')
            with open(os.path.join(BASE, 'subs.jsonl'), 'a') as f:
                f.write(json.dumps(sub) + '\n')
            self.send_response(200); self._cors()
            self.send_header('Content-Type', 'application/json'); self.end_headers()
            self.wfile.write(b'{"ok": true}'); return
        if self.path != '/upload':
            return self._deny(404, 'not found')
        if self.headers.get('X-Party') != PARTY:
            return self._deny(403, 'wrong party')
        n = int(self.headers.get('Content-Length', 0))
        if not (0 < n <= MAX_BYTES):
            return self._deny(413, 'too big')
        data = self.rfile.read(n)
        if not data.startswith(b'\xff\xd8'):
            return self._deny(415, 'jpeg only')
        guest = re.sub(r'[^A-Za-z0-9_-]', '', self.headers.get('X-Guest', 'guest'))[:24] or 'guest'
        name = f"{guest}_{int(time.time()*1000)}.jpg"
        with open(os.path.join(PHOTOS, name), 'wb') as f:
            f.write(data)
        self.send_response(200); self._cors()
        self.send_header('Content-Type', 'application/json'); self.end_headers()
        self.wfile.write(json.dumps({'ok': True, 'name': name}).encode())

    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path == '/health':
            self.send_response(200); self._cors(); self.end_headers()
            self.wfile.write(b'ok'); return
        if path == '/vapid':
            with open(os.path.join(BASE, 'keys', 'public_key.txt')) as f:
                k = f.read().strip()
            self.send_response(200); self._cors()
            self.send_header('Content-Type', 'application/json'); self.end_headers()
            self.wfile.write(json.dumps({'key': k}).encode()); return
        if not self._pin_ok():
            return self._deny(403, 'pin')
        if path == '/list':
            fs = sorted(os.listdir(PHOTOS))
            out = [{'name': f, 'size': os.path.getsize(os.path.join(PHOTOS, f))}
                   for f in fs if f.endswith('.jpg')]
            self.send_response(200); self._cors()
            self.send_header('Content-Type', 'application/json'); self.end_headers()
            self.wfile.write(json.dumps({'count': len(out), 'photos': out}).encode()); return
        if path.startswith('/photos/'):
            f = re.sub(r'[^A-Za-z0-9_.-]', '', path.split('/photos/', 1)[1])
            fp = os.path.join(PHOTOS, f)
            if not os.path.isfile(fp):
                return self._deny(404, 'gone')
            self.send_response(200); self._cors()
            self.send_header('Content-Type', 'image/jpeg')
            self.send_header('Content-Length', str(os.path.getsize(fp)))
            self.end_headers()
            with open(fp, 'rb') as fh:
                self.wfile.write(fh.read())
            return
        if path == '/zip':
            q = (self.path.split('?', 1) + [''])[1]
            guest = ''
            for part in q.split('&'):
                if part.startswith('guest='):
                    guest = re.sub(r'[^A-Za-z0-9_-]', '', part[6:])
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, 'w', zipfile.ZIP_STORED) as z:
                for f in sorted(os.listdir(PHOTOS)):
                    if f.endswith('.jpg') and (not guest or f.startswith(guest + '_')):
                        z.write(os.path.join(PHOTOS, f), f)
            b = buf.getvalue()
            self.send_response(200); self._cors()
            self.send_header('Content-Type', 'application/zip')
            self.send_header('Content-Disposition', 'attachment; filename="mia-party-photos.zip"')
            self.send_header('Content-Length', str(len(b)))
            self.end_headers()
            self.wfile.write(b); return
        self._deny(404, 'not found')

    def log_message(self, fmt, *a):
        pass

class TS(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

if __name__ == '__main__':
    TS(('127.0.0.1', 8098), H).serve_forever()
