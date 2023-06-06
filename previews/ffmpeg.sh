#!/bin/bash
mkdir -p /usr/local/etc/ffmpeg
cd /usr/local/etc/ffmpeg
mkdir build
mkdir bin
git clone https://github.com/FFmpeg/FFmpeg.git source
cd source
if [ $1 == "x264" ]
then
  echo "x264"
  PKG_CONFIG_PATH="/usr/local/lib/pkgconfig" ./configure \
  --prefix="/usr/local/etc/ffmpeg/build" \
  --pkg-config-flags="--static" \
  --extra-cflags="-I/usr/local/include" \
  --extra-ldflags="-L/usr/local/lib" \
  --extra-libs="-lpthread -lm" \
  --ld="g++" \
  --bindir="/usr/local/etc/ffmpeg/bin" \
  --enable-gpl \
  --enable-libvpx \
  --enable-libx264 \
  --enable-static \
  --enable-shared \
  --enable-gnutls && \
  PATH="$HOME/bin:$PATH" make -j$(nproc) && \
  make install && \
  hash -r
else # anything else doesn't need to enable gpl
  PKG_CONFIG_PATH="/usr/local/lib/pkgconfig" ./configure \
  --prefix="/usr/local/etc/ffmpeg/build" \
  --pkg-config-flags="--static" \
  --extra-cflags="-I/usr/local/include" \
  --extra-ldflags="-L/usr/local/lib" \
  --extra-libs="-lpthread -lm" \
  --ld="g++" \
  --bindir="/usr/local/etc/ffmpeg/bin" \
  --enable-libopenh264 \
  --enable-static \
  --enable-libvpx \
  --enable-shared \
  --enable-libvorbis \
  --enable-libsvtav1 \
  --enable-gnutls && \
  PATH="$HOME/bin:$PATH" make -j$(nproc) && \
  make install && \
  hash -r
fi 