FROM php:7.2-apache

RUN add-apt-repository ppa:savoury1/ffmpeg4 && \
  apt update && \
  apt install ffmpeg
