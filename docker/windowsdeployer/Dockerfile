# syntax=docker/dockerfile:experimental

FROM ghcr.io/cmahnke/windows-deployer/msitools:latest as msitools

FROM ghcr.io/cmahnke/windows-deployer/fileprovider:latest

LABEL maintainer="cmahnke@gmail.com"
LABEL org.opencontainers.image.source=https://github.com/cmahnke/windows-deployer

ENV REQ_RUN="openssl" \
    REQ_BUILD="git gcc musl-dev python3-dev libffi-dev openssl-dev cargo" \
    BUILD_DIR="/build"

COPY --from=msitools /build/msitools/*.apk /build/

RUN --mount=target=/mnt/build-context \
    echo "http://dl-cdn.alpinelinux.org/alpine/edge/community" >> /etc/apk/repositories && \
    apk update && \
    apk add --no-cache $REQ_RUN $REQ_BUILD && \
    apk add --allow-untrusted --no-cache $BUILD_DIR/msitools-[0-9]*.apk && \
    pip install --upgrade pip && \
    pip install -r /mnt/build-context/docker/windowsdeployer/requirements.txt && \
    cp -Lr /mnt/build-context/docker/windowsdeployer/scripts/* $SCRIPT_DIR && \
    mkdir -p $BUILD_DIR && \
    cd $BUILD_DIR && \
    cp -r /mnt/build-context/submodules/impacket $BUILD_DIR/ && \
    python3 -m pip install impacket/ && \
    cd / && \
    apk del $REQ_BUILD && \
    rm -rf $BUILD_DIR /var/lib/apt/lists/*

ENTRYPOINT ["/bin/sh"]