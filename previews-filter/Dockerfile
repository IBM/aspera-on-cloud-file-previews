# Define function directory
ARG FUNCTION_DIR="/function"

FROM python:3.9.16-bullseye as build-image

# Install aws-lambda-cpp build dependencies
RUN apt-get update && \
  apt-get install -y \
  g++ \
  make \
  cmake \
  unzip \
  libcurl4-openssl-dev

# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Create function directory
RUN mkdir -p ${FUNCTION_DIR}

# Copy function code
COPY / ${FUNCTION_DIR}

# Install the runtime interface client
RUN pip install --upgrade pip && \
    pip install --target ${FUNCTION_DIR} \
    awslambdaric \
    pyyaml \
    boto3

# Multi-stage build: grab a fresh copy of the base image
FROM python:3.9.16-bullseye as base

# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Set working directory to function root directory
WORKDIR ${FUNCTION_DIR}

# Copy in the build image dependencies
COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}

# (Optional) Add Lambda Runtime Interface Emulator and use a script in the ENTRYPOINT for simpler local runs
ADD https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie /usr/bin/aws-lambda-rie
COPY entry.sh /
RUN chmod 755 /usr/bin/aws-lambda-rie /entry.sh

RUN useradd -M -d ${FUNCTION_DIR} -u 1000 app \
    && chown -R app:app ${FUNCTION_DIR}

USER app

ENTRYPOINT [ "/entry.sh" ]     