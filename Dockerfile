FROM php:7.2-apache

RUN sed -i 's/deb.debian.org/archive.debian.org/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/archive.debian.org/g' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y ffmpeg cron php7.2-mysql
