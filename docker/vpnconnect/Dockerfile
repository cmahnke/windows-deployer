# syntax=docker/dockerfile:experimental

FROM python:3.14.3-alpine

LABEL maintainer="cmahnke@gmail.com"
LABEL org.opencontainers.image.source=https://github.com/cmahnke/windows-deployer

ENV REQ_RUN="openconnect bash procps" \
    REQ_BUILD="shadow" \
    SCRIPT_DIR="/opt/entrypoint" \
    PATH=":$PATH"

RUN --mount=target=/mnt/build-context \
    apk update && \
    apk add --no-cache --update $REQ_BUILD $REQ_RUN && \
    pip install --upgrade pip && \
    pip install -r /mnt/build-context/docker/vpnconnect/requirements.txt && \
    mkdir -p $SCRIPT_DIR && \
    cp -Lr /mnt/build-context/docker/vpnconnect/scripts/* $SCRIPT_DIR && \
    cp /mnt/build-context/submodules/vpnc-scripts/vpnc-script /etc/vpnc/vpnc-script && \
    chmod +x /etc/vpnc/vpnc-script && \
    usermod -s /bin/bash root && \
    apk del $REQ_BUILD && \
    rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["/bin/sh"]
#COMMAND ["$SCRIPT_DIR/run.py"]
