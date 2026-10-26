#!/usr/bin/env python3
"""Build-independent integration checks. Requires Docker and Python's stdlib only."""

import hashlib
import http.client
import http.cookiejar
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request


def command(*args):
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Command failed: {args}\n{result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python3 tests/smoke.py IMAGE')
    image = sys.argv[1]
    tests = Path(__file__).resolve().parent
    expected = json.loads((tests / 'expectations.json').read_text())
    version = expected['php']
    extensions = {
        'ctype', 'curl', 'dom', 'fileinfo', 'filter', 'ftp', 'hash', 'iconv',
        'json', 'mbstring', 'mysqli', 'mysqlnd', 'openssl', 'pcre', 'PDO',
        'pdo_mysql', 'pdo_sqlite', 'Phar', 'posix', 'session', 'SimpleXML',
        'sodium', 'SPL', 'sqlite3', 'tokenizer', 'xml', 'xmlreader', 'xmlwriter',
        'Zend OPcache', 'zlib',
    }
    extensions.update(['imagick'] if expected['kind'] == 'ffmpeg'
                      else ['gd', 'intl', 'zip'])
    container = command('docker', 'run', '-d', '--memory=512m', '--pids-limit=128',
                        '-p', '127.0.0.1::80', image)

    def execute(*args):
        return command('docker', 'exec', container, *args)

    def php(code):
        return execute('php', '-r', code)

    try:
        command('docker', 'cp', str(tests / 'probe.php'),
                f"{container}:{expected['document_root']}/index.php")
        if expected['rewrite']:
            with tempfile.TemporaryDirectory() as directory:
                htaccess = Path(directory) / '.htaccess'
                htaccess.write_text('RewriteEngine On\nRewriteRule ^rewritten$ index.php [L]\n')
                command('docker', 'cp', str(htaccess),
                        f"{container}:{expected['document_root']}/.htaccess")

        binding = json.loads(command('docker', 'inspect', container))[0]
        require(binding['State']['Running'], 'Apache exited during startup')
        port = binding['NetworkSettings']['Ports']['80/tcp'][0]['HostPort']
        base = f'http://127.0.0.1:{port}'
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

        def request(path='/', data=None, headers=None):
            req = urllib.request.Request(base + path, data=data, headers=headers or {})
            with opener.open(req, timeout=5) as response:
                require(response.status == 200, f'HTTP status: {response.status}')
                return json.load(response)

        def ready():
            last_error = None
            for _ in range(40):
                try:
                    return request()
                except (OSError, ValueError, http.client.HTTPException) as error:
                    last_error = error
                    time.sleep(0.25)
            raise RuntimeError(f'Apache did not become ready: {last_error}')

        web = ready()
        require(web['version'].startswith(version + '.'), f'Wrong PHP version: {web}')
        require(web['sapi'] == 'apache2handler', f'Wrong Apache handler: {web}')
        require(not extensions.difference(web['extensions']),
                f"Missing web extensions: {extensions.difference(web['extensions'])}")
        require(web['upload_progress'] in ('', '0'), 'Web upload progress still enabled')
        require(web['gc_probability'] == '1', 'PHP session cleanup is disabled')
        require(web['uid'] == web['gid'] == expected['uid'], f'Wrong Apache user: {web}')
        require(web['database'] == 'ok', 'PDO SQLite query failed')
        for key, value in expected['settings'].items():
            require(web[key] == value, f'{key}: expected {value}, got {web[key]}')

        cli = json.loads(php('echo json_encode(array("version" => PHP_VERSION, '
                             '"extensions" => get_loaded_extensions(), '
                             '"upload_progress" => ini_get("session.upload_progress.enabled")));'))
        require(cli['version'] == web['version'], 'CLI and Apache PHP versions differ')
        require(not extensions.difference(cli['extensions']),
                f"Missing CLI extensions: {extensions.difference(cli['extensions'])}")
        require(cli['upload_progress'] in ('', '0'), 'CLI upload progress still enabled')
        for package in (f'php{version}-cli', f'php{version}-common', f'libapache2-mod-php{version}'):
            installed = execute('dpkg-query', '-W', '-f=${Version}', package)
            execute('dpkg', '--compare-versions', installed, 'ge', expected['minimum_package'])
            print(f'  {package}: {installed}', flush=True)
        execute('apache2ctl', '-t')

        second = request()
        require(second['visits'] == web['visits'] + 1, 'Session did not survive the next request')
        if expected['rewrite']:
            require(request('/rewritten')['sapi'] == 'apache2handler', '.htaccess rewrite failed')
        if expected['forwarded_https']:
            require(request(headers={'X-Forwarded-Proto': 'https'})['https'] == 'on',
                    'Reverse proxy HTTPS detection failed')

        payload = b'upload smoke test\x00\xff\n'
        boundary = 'php-image-smoke-boundary'
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
                'filename="test.bin"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()
        body += payload + f'\r\n--{boundary}--\r\n'.encode()
        uploaded = request(data=body, headers={
            'Content-Type': f'multipart/form-data; boundary={boundary}'})['upload']
        require(uploaded == {'error': 0, 'uploaded': True,
                             'sha256': hashlib.sha256(payload).hexdigest()},
                f'File upload failed: {uploaded}')

        if expected['kind'] == 'ffmpeg':
            execute('ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'lavfi',
                    '-i', 'color=c=blue:s=32x32:d=0.1', '-c:v', 'libx264',
                    '-pix_fmt', 'yuv420p', '-y', '/tmp/smoke.mp4')
            codec = execute('ffprobe', '-v', 'error', '-select_streams', 'v:0',
                            '-show_entries', 'stream=codec_name', '-of',
                            'default=noprint_wrappers=1:nokey=1', '/tmp/smoke.mp4')
            require(codec == 'h264', f'FFmpeg encoding failed: {codec}')
            require(php('$i = new Imagick(); $i->newImage(8, 8, "red"); '
                        '$i->setImageFormat("png"); echo strlen($i->getImageBlob()) > 0 ? "ok" : "fail";')
                    == 'ok', 'Imagick PNG generation failed')
            execute('mariadb', '--version')
            if expected['cron']:
                execute('dpkg-query', '-W', 'cron')
        else:
            require('Composer version 2.2.' in execute('composer', '--version'),
                    'Composer 2.2 LTS missing')
            gd = json.loads(php('echo json_encode(gd_info());'))
            require(gd['JPEG Support'] and gd['FreeType Support'] and gd['PNG Support'],
                    f'GD image capabilities missing: {gd}')
            require(php('$i = imagecreatetruecolor(8, 8); '
                        'echo imagepng($i, "/tmp/smoke.png") ? "ok" : "fail";') == 'ok',
                    'GD PNG generation failed')
            require(php('echo transliterator_transliterate("Any-Latin; Latin-ASCII", "Äpfel");')
                    == 'Apfel', 'ICU transliteration failed')
            require(php('$z = new ZipArchive(); $z->open("/tmp/smoke.zip", ZipArchive::CREATE); '
                        '$z->addFromString("test.txt", "ok"); $z->close(); '
                        '$z->open("/tmp/smoke.zip"); echo $z->getFromName("test.txt");') == 'ok',
                    'ZIP round trip failed')

        # A normal allocation failure must not leave Apache unable to serve requests.
        try:
            with opener.open(base + '/?oom=1', timeout=5) as response:
                response.read()
                raise RuntimeError('Memory exhaustion unexpectedly returned HTTP 200')
        except urllib.error.HTTPError as error:
            require(error.code >= 500, f'Unexpected OOM status: {error.code}')
        except (urllib.error.URLError, http.client.HTTPException, ConnectionError):
            pass
        ready()
        command('docker', 'restart', '-t', '10', container)
        # Docker may assign a new ephemeral host port when restarting.
        binding = json.loads(command('docker', 'inspect', container))[0]
        port = binding['NetworkSettings']['Ports']['80/tcp'][0]['HostPort']
        base = f'http://127.0.0.1:{port}'
        ready()
        logs = command('docker', 'logs', container)
        require('GET /' in logs, 'Apache access logs are not forwarded to Docker')
        print(f'PASS {image}: CLI, Apache, extensions, sessions, uploads, tools, '
              'OOM recovery and restart', flush=True)
    except BaseException:
        subprocess.run(['docker', 'logs', '--tail', '80', container], check=False)
        raise
    finally:
        subprocess.run(['docker', 'rm', '-f', container], check=False,
                       stdout=subprocess.DEVNULL)


if __name__ == '__main__':
    main()
