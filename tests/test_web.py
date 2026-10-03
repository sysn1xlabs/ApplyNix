import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

class WebTests(unittest.TestCase):
    def test_dashboard_prepare_approve_and_origin_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
            process = subprocess.Popen([sys.executable, '-m', 'applynix', '--home', directory, 'serve', '--port', str(port)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            base = f'http://127.0.0.1:{port}'
            try:
                for _ in range(100):
                    try:
                        page = urllib.request.urlopen(base, timeout=1).read().decode(); break
                    except (OSError, urllib.error.URLError): time.sleep(.02)
                else: self.fail('Dashboard did not start')
                self.assertIn('Make every application count.', page)
                def post(path, body, origin=base):
                    request = urllib.request.Request(base + path, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'Origin': origin})
                    return json.loads(urllib.request.urlopen(request).read())
                body = {'profile': {'personal': {'name': '<img src=x onerror=alert(1)>'}, 'skills': ['Windows']}, 'job': 'Title: Support\nRequired:\nWindows'}
                with self.assertRaises(urllib.error.HTTPError) as error:
                    post('/api/prepare', body, 'http://evil.example')
                self.assertEqual(error.exception.code, 403)
                identity = post('/api/prepare', body)['id']
                with self.assertRaises(urllib.error.HTTPError): post('/api/approve', {'id': identity, 'confirmation': 'yes'})
                post('/api/approve', {'id': identity, 'confirmation': 'APPROVE ' + identity})
                record = json.loads(urllib.request.urlopen(base + '/api/application/' + identity).read())
                self.assertEqual(record['status'], 'READY')
                self.assertEqual(len(record['events']), 2)
            finally:
                process.terminate(); process.communicate(timeout=5)

if __name__ == '__main__': unittest.main()
