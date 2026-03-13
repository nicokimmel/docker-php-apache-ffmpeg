FROM php:7.2-apache

# Fix outdated Debian sources
RUN sed -i 's/deb.debian.org/archive.debian.org/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/archive.debian.org/g' /etc/apt/sources.list

# Install dependencies, ImageMagick, PHP extensions
RUN apt-get update && apt-get install -y \
        ffmpeg \
        cron \
        libonig-dev \
        libzip-dev \
        libpng-dev \
        libjpeg-dev \
        libfreetype6-dev \
        mariadb-client \
        imagemagick \
        libmagickwand-dev \
        --no-install-recommends \
    && docker-php-ext-install pdo_mysql mysqli \
    && pecl install imagick \
    && docker-php-ext-enable imagick \
    && rm -rf /var/lib/apt/lists/*
