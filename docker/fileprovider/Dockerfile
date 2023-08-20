# syntax=docker/dockerfile:experimental

FROM ghcr.io/cmahnke/windows-deployer/vpnconnect:latest

LABEL maintainer="cmahnke@gmail.com"
LABEL org.opencontainers.image.source=https://github.com/cmahnke/windows-deployer

ENV REQ_RUN="samba-server samba-common-tools bash" \
    REQ_BUILD="git gcc musl-dev python3-dev libffi-dev" \
    SMB_USERNAME=Administrator \
    SMB_PASSWORD=changeme

RUN --mount=target=/mnt/build-context \
    echo "http://dl-cdn.alpinelinux.org/alpine/edge/testing" >> /etc/apk/repositories && \
    apk update && \
    apk add --no-cache --update $REQ_RUN $REQ_BUILD && \
    adduser -D $SMB_USERNAME && \
    (echo $SMB_PASSWORD; echo $SMB_PASSWORD) | smbpasswd -a $SMB_USERNAME && \
    chown -R $SMB_USERNAME /srv && \
    pip install --upgrade pip && \
    pip install -r /mnt/build-context/docker/fileprovider/requirements.txt && \
    cp -Lr /mnt/build-context/docker/fileprovider/scripts/* $SCRIPT_DIR && \
    mkdir /usr/local/sbin && \
    chmod go-rx /usr/local/sbin/ && \
    mv $SCRIPT_DIR/add_user_script /usr/local/sbin/add_user_script && \
    cp /mnt/build-context/docker/fileprovider/smb.conf /etc/samba/smb.conf && \
    apk del $REQ_BUILD && \
    rm -rf $BUILD_DIR /var/lib/apt/lists/*

EXPOSE 445/tcp

ENTRYPOINT ["/bin/bash"]