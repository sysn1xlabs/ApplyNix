"""Loopback-only dashboard. No external resources or application submission."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from importlib.resources import files
from urllib.parse import urlparse
from .core import prepare, export

def serve(store, home, port):
    class Handler(BaseHTTPRequestHandler):
        def respond(self, body, mime='application/json', status=200):
            data = body.encode()
            self.send_response(status)
            self.send_header('Content-Type', mime + '; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; frame-ancestors 'none'; connect-src 'self'")
            self.end_headers(); self.wfile.write(data)
        def valid_host(self):
            return self.headers.get('Host') in {f'127.0.0.1:{port}', f'localhost:{port}'}
        def do_GET(self):
            if not self.valid_host():
                return self.respond('{}', status=403)
            path = urlparse(self.path).path
            try:
                if path == '/':
                    self.respond(files('applynix').joinpath('dashboard.html').read_text(encoding='utf-8'), 'text/html')
                elif path == '/api/history':
                    self.respond(json.dumps(store.list()))
                elif path.startswith('/api/application/'):
                    record = store.get(path.rsplit('/', 1)[-1])
                    record['events'] = store.events(record['id'])
                    self.respond(json.dumps(record))
                else:
                    self.respond('{}', status=404)
            except ValueError as exc:
                self.respond(json.dumps({'error': str(exc)}), status=400)
        def do_POST(self):
            origin = self.headers.get('Origin')
            if not self.valid_host() or origin not in {f'http://127.0.0.1:{port}', f'http://localhost:{port}'} or self.headers.get('Content-Type') != 'application/json':
                return self.respond('{}', status=403)
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 1000000:
                    return self.respond('{}', status=413)
                body = json.loads(self.rfile.read(size))
                if self.path == '/api/prepare':
                    bundle = prepare(body['profile'], body['job'])
                    identity = store.save(bundle)
                    export(bundle, home / 'applications' / identity)
                    self.respond(json.dumps({'id': identity}))
                elif self.path == '/api/approve':
                    if body.get('confirmation') != 'APPROVE ' + body['id']:
                        raise ValueError('Exact approval phrase required.')
                    store.status(body['id'], 'READY', 'User reviewed and approved exact draft in dashboard.')
                    self.respond('{}')
                else:
                    self.respond('{}', status=404)
            except (ValueError, KeyError, TypeError, OSError) as exc:
                self.respond(json.dumps({'error': str(exc)}), status=400)
        def log_message(self, *args):
            pass
    server = HTTPServer(('127.0.0.1', port), Handler)
    print(f'ApplyNix dashboard: http://127.0.0.1:{port} — Ctrl+C to stop', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
