# Define function directory
ARG FUNCTION_DIR="/function"
ARG encoder

FROM python:3.9.16-bullseye as build-image

# Necessary to install the latest version of cmake (needs at least 3.16 to build libsvtav1)
RUN wget -O - https://apt.kitware.com/keys/kitware-archive-latest.asc 2>/dev/null | gpg --dearmor - | tee /usr/share/keyrings/kitware-archive-keyring.gpg >/dev/null \
    && echo 'deb [signed-by=/usr/share/keyrings/kitware-archive-keyring.gpg] https://apt.kitware.com/ubuntu/ bionic main' | tee /etc/apt/sources.list.d/kitware.list >/dev/null

RUN apt-get update && apt-get install -y software-properties-common

RUN apt-add-repository 'deb https://apt.kitware.com/ubuntu/ bionic main'

# Install aws-lambda-cpp build dependencies
# All the packages beyond libcurl4-openssl-dev are necessary to build ffmpeg
RUN apt-get update && \
  apt-get install -y \
  g++ \
  make \
  cmake \
  unzip \
  libcurl4-openssl-dev \ 
  autoconf \
  automake \
  build-essential \
  git-core \
  libass-dev \
  libfreetype6-dev \
  libunistring-dev \
  libgnutls28-dev \
  libmp3lame-dev \
  libsdl2-dev \
  libtool \
  libva-dev \
  libvdpau-dev \
  libvorbis-dev \
  libxcb1-dev \
  libxcb-shm0-dev \
  libxcb-xfixes0-dev \
  libvpx-dev \
  meson \
  ninja-build \
  pkg-config \
  texinfo \
  wget \
  yasm \
  zlib1g-dev \
  libx264-dev \
  nasm

ARG encoder

ADD encoders.sh /
ADD ffmpeg.sh /
RUN chmod +x /encoders.sh /ffmpeg.sh

# Downloads openh264 source code and build it
RUN /encoders.sh
# Builds ffmpeg enabling openh264 since it's already installed
RUN /ffmpeg.sh $encoder

# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Create function directory
RUN mkdir -p ${FUNCTION_DIR}

# Copy function code
COPY main__.py ${FUNCTION_DIR}
COPY file_formats.yml ${FUNCTION_DIR}
COPY main_thumb.yml ${FUNCTION_DIR}

# Install the runtime interface client
RUN pip install --upgrade pip && \
    pip install --target ${FUNCTION_DIR} \
    awslambdaric \
    pyyaml \
    boto3 \
    ibm-cos-sdk

# Multi-stage build: grab a fresh copy of the base image
FROM python:3.9.16-bullseye as base

RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y imagemagick optipng ghostscript ffmpeg

COPY policy.xml /etc/ImageMagick-6/

# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Set working directory to function root directory
WORKDIR ${FUNCTION_DIR}

# Copy in the build image dependencies
COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}

# Only copy ffmpeg build directory so that it complains about not finding the shared object for openh264
COPY --from=build-image /usr/local/etc/ffmpeg ${FUNCTION_DIR}

# Get cisco binary to avoid MPEG LA license fees
RUN wget http://ciscobinary.openh264.org/libopenh264-2.1.0-linux64.5.so.bz2
RUN bzip2 -d libopenh264-* -c > libopenh264.so
RUN mv libopenh264.so /function/build/lib/libopenh264.so.5
COPY --from=build-image /usr/local/lib/libSvtAv1Enc.so /function/build/lib/libSvtAv1Enc.so.1

FROM base AS branch-openh264

RUN mv /function/build/lib/libopenh264.so.5 /usr/local/lib/

FROM base AS branch-x264

RUN mv /usr/lib/x86_64-linux-gnu/libx264* /usr/local/lib/

FROM base as branch-av1

RUN mv /function/build/lib/libSvtAv1Enc.so.1 /usr/local/lib/

FROM base as branch-vp9
# Since vp9 is the default option, then there's no need to move its file
RUN echo vp9

FROM branch-${encoder} AS final

# Create config file so that ffmpeg is able to find more .so files
RUN echo '/function/build/lib' > /etc/ld.so.conf.d/ffmpeg.conf
RUN ldconfig

# (Optional) Add Lambda Runtime Interface Emulator and use a script in the ENTRYPOINT for simpler local runs
ADD https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie /usr/bin/aws-lambda-rie
COPY entry.sh /
RUN chmod 755 /usr/bin/aws-lambda-rie /entry.sh

RUN useradd -M -d /function -u 1000 app \
    && chown -R app:app /function

USER app

ENTRYPOINT [ "/entry.sh" ]

