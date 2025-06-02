# syntax=docker/dockerfile:experimental

FROM alpine:3.22

LABEL maintainer="cmahnke@gmail.com"
LABEL org.opencontainers.image.source=https://github.com/cmahnke/windows-deployer

ENV REQ_RUN="" \
    REQ_BUILD="alpine-sdk sudo" \
    BUILD_DIR="/build" \
    BUILD_USER=abuilder \
    APK_REPO=https://gitlab.alpinelinux.org/alpine/aports \
    APK_BUILD=community/msitools/APKBUILD

RUN --mount=target=/mnt/build-context \
    apk update && \
    apk add --no-cache --update $REQ_RUN $REQ_BUILD && \
    adduser -D $BUILD_USER && \
    adduser $BUILD_USER wheel && \
    addgroup $BUILD_USER abuild && \
    echo '%wheel ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/wheel && \
    mkdir -p /var/cache/distfiles && \
    chgrp abuild /var/cache/distfiles && \
    chmod g+w /var/cache/distfiles && \
    mkdir -p $BUILD_DIR/msitools && \
    cd $BUILD_DIR && \
    wget -O msitools/APKBUILD "$APK_REPO/-/raw/master/$APK_BUILD?inline=false" && \
    cp /mnt/build-context/patches/wixl-arm64.patch $BUILD_DIR/msitools/ && \
    sed -i -E 's/source="(.*)"/source="\1\nwixl-arm64.patch"/g' msitools/APKBUILD && \
    chown -R $BUILD_USER $BUILD_DIR

USER ${BUILD_USER}
RUN cd $BUILD_DIR/msitools && \
    abuild-keygen -a -i -n && \
    abuild checksum && \
    abuild -r && \
    mv ~/packages/build/* $BUILD_DIR/

USER root
RUN deluser --remove-home $BUILD_USER && \
    rm -rf $BUILD_DIR/msitools && \
    ln -s $BUILD_DIR/`uname -m` $BUILD_DIR/msitools && \
    apk del $REQ_BUILD && \
    rm -rf /var/lib/apt/lists/* 