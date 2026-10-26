# docker-php-apache-ffmpeg

## Debian / Sury migration

This branch uses `debian:trixie-slim`, Debian Apache and the PHP 7.2
packages from [Sury](https://packages.sury.org/php/). PHP stays on the same
minor version. The Apache document root remains `/var/www/html`.
The published image tag remains `7.2`.

The Dockerfile verifies the full Debian package revision of PHP CLI, common
and the Apache module against the patched 2026-10-21 build (7.2.34-66).
These packages include the minimal EOL backport for **CVE-2026-109618** and
**CVE-2026-109619**. `php -v` alone cannot identify this backport.
This does not restore upstream security support for PHP 7.2.

- [PHP security advisory](https://www.php.net/archive/2026.php#2026-10-21-5)
- [Sury source and binary packages](https://packages.sury.org/php/pool/main/p/php7.2/)

### Configuration changes

PHP extensions now come from versioned Debian packages; the
`docker-php-ext-*` build helpers are no longer available.

Custom PHP configuration belongs in `/etc/php/7.2/apache2/conf.d/`
for web requests and `/etc/php/7.2/cli/conf.d/` for command-line jobs.
Migrate any mounts targeting `/usr/local/etc/php/` to these paths.
The bundled `docker/php.ini` is enabled for both SAPIs through `phpenmod`.

Session upload progress is disabled; ordinary file uploads remain enabled.
PHP performs session garbage collection because the container does not run
Debian's scheduled session-cleanup service. Apache runs in the foreground
and sends access/error logs to Docker. Commands such as `docker run --rm
IMAGE php -v` still work through the entrypoint.

The OS upgrade also changes system libraries and tools. Validate the actual
application, extensions, database connection and representative media files
before replacing production containers.

### Build and test

```sh
docker build --pull --no-cache -t local/docker-php-apache-ffmpeg:7.2 .
python3 tests/smoke.py local/docker-php-apache-ffmpeg:7.2
```

Use `--no-cache` when refreshing security packages: pulling the base image
alone does not invalidate an already cached Sury installation layer.
Existing containers must be recreated from the new image.

The tests need Docker and Python 3 only. They start a disposable container
on a random localhost port and remove it afterwards. They check the package
revision, CLI and Apache PHP, required extensions, sessions, multipart uploads,
branch-specific settings, tools, recovery after memory exhaustion and restart.
Test fixtures are excluded from the image. These are image integration tests,
not a complete application test or an exploit-based security assessment.

GitHub Actions runs the same tests before publishing. Pull requests build and
test without publishing; pushes and manual workflow runs retain the existing
tag naming. No registry credentials are needed for local tests.
