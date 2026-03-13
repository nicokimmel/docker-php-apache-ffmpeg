FROM php:7.2-apache

RUN apt update && \
    apt install -y software-properties-common && \
    add-apt-repository ppa:savoury1/ffmpeg4 && \
    apt update && \
    apt install -y ffmpeg
