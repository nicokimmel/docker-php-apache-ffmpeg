FROM php:7.2-apache

RUN sed -i 's/deb.debian.org/archive.debian.org/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/archive.debian.org/g' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y ffmpeg cron libonig-dev libzip-dev libpng-dev libjpeg-dev libfreetype6-dev mariadb-client \
    && docker-php-ext-install pdo_mysql \
    && docker-php-ext-install mysqli \
    && docker-php-ext-enable pdo_mysql
