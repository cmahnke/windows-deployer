# syntax=docker/dockerfile:experimental

FROM ghcr.io/cmahnke/windows-deployer/msitools:latest as msitools

FROM golang:1.22-alpine as builder

ENV MOD_DIR=/go/src/christianmahnke.de/examples/windowsdeployer \
    GOOS=windows \
    ARCHS="amd64 arm64"

RUN --mount=target=/mnt/build-context \
    mkdir -p $MOD_DIR && \
    cp -r /mnt/build-context/docker/deployexample/*.go /mnt/build-context/docker/deployexample/go.* $MOD_DIR && \
    cd $MOD_DIR && \
    for ARCH in amd64 arm64; do \
        CGO_ENABLED=0 GOARCH=$ARCH CGO_ENABLED=0 go build -o deployexample-$ARCH.exe; \
    done
    
FROM alpine:3.20

LABEL maintainer="cmahnke@gmail.com"
LABEL org.opencontainers.image.source=https://github.com/cmahnke/windows-deployer

ENV REQ_BUILD="xmlstarlet" \
    BUILD_DIR=/build \
    MOD_DIR=/go/src/christianmahnke.de/examples/windowsdeployer \
    WIX_TEMPLATE=deployexample.wxs

COPY --from=builder $MOD_DIR/deployexample* /build/
COPY --from=msitools /build/msitools/*.apk /build/

RUN --mount=target=/mnt/build-context \
    mkdir -p $BUILD_DIR && \
    echo "http://dl-cdn.alpinelinux.org/alpine/edge/community" >> /etc/apk/repositories && \
    apk update && \
    apk add --no-cache $REQ_BUILD && \
    apk add --allow-untrusted --no-cache $BUILD_DIR/msitools-[0-9]*.apk && \
    cp /mnt/build-context/docker/deployexample/deployexample.wxs $BUILD_DIR && \
    cd $BUILD_DIR/ && \
    for ARCH in amd64 arm64; do \
        sed -E "s/deployexample.exe/deployexample-$ARCH.exe/g" $BUILD_DIR/$WIX_TEMPLATE > `basename $WIX_TEMPLATE .wxs`"-$ARCH.wxs" && \
        /usr/bin/wixl -a $ARCH -v -o "deployexample-$ARCH.msi" `basename $WIX_TEMPLATE .wxs`"-$ARCH.wxs"; \
    done && \
    apk del $REQ_BUILD msitools && \
    rm -rf $BUILD_DIR/msitools-* /var/lib/apt/lists/*
