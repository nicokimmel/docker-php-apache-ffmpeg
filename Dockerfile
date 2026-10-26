FROM debian:trixie-slim

# Sury supplies backports for the EOL PHP branches. Trust only its dedicated keyring.
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl; \
    curl -fsSL --retry 3 https://packages.sury.org/debsuryorg-archive-keyring.deb -o /tmp/sury-keyring.deb; \
    dpkg -i /tmp/sury-keyring.deb; \
    rm /tmp/sury-keyring.deb; \
    echo 'deb [signed-by=/usr/share/keyrings/debsuryorg-archive-keyring.gpg] https://packages.sury.org/php/ trixie main' > /etc/apt/sources.list.d/php.list; \
    rm -rf /var/lib/apt/lists/*

# These revisions contain the backport for CVE-2026-109618 and CVE-2026-109619.
# Check the Debian package version: PHP_VERSION alone does not identify backports.
RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        apache2 \
        ca-certificates \
        curl \
        libapache2-mod-php7.2 \
        php7.2-cli \
        php7.2-common \
        php7.2-curl \
        php7.2-json \
        php7.2-mbstring \
        php7.2-mysql \
        php7.2-opcache \
        php7.2-readline \
        php7.2-sqlite3 \
        php7.2-xml \
        php7.2-imagick \
        ffmpeg \
        imagemagick \
        mariadb-client; \
    for package in php7.2-cli php7.2-common libapache2-mod-php7.2; do \
        installed="$(dpkg-query -W -f='${Version}' "$package")"; \
        dpkg --compare-versions "$installed" ge '7.2.34-66+0~20261021.122+debian13~1.gbpe0bcd4'; \
    done; \
    a2dismod mpm_event; \
    a2enmod mpm_prefork php7.2 rewrite headers expires deflate filter setenvif; \
    rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    groupmod -o -g 1000 www-data; \
    usermod -o -u 1000 -g 1000 www-data; \
    chown www-data:www-data /var/lib/php/sessions

COPY docker/apache-site.conf /etc/apache2/sites-available/000-default.conf
COPY docker/php.ini /etc/php/7.2/mods-available/application.ini
COPY docker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN set -eux; \
    phpenmod -v 7.2 -s ALL application; \
    chmod +x /usr/local/bin/docker-entrypoint.sh; \
    mkdir -p /var/www/html; \
    rm -f /var/www/html/index.html; \
    ln -sf /proc/self/fd/1 /var/log/apache2/access.log; \
    ln -sf /proc/self/fd/1 /var/log/apache2/other_vhosts_access.log; \
    ln -sf /proc/self/fd/2 /var/log/apache2/error.log

WORKDIR /var/www/html
EXPOSE 80
STOPSIGNAL SIGWINCH
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["apache2-foreground"]
