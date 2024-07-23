#!/bin/sh

docker buildx build -f docker/msitools/Dockerfile -t ghcr.io/cmahnke/windows-deployer/msitools:latest .
docker buildx build -f docker/vpnconnect/Dockerfile -t ghcr.io/cmahnke/windows-deployer/vpnconnect:latest .
docker buildx build -f docker/fileprovider/Dockerfile -t ghcr.io/cmahnke/windows-deployer/fileprovider:latest .
docker buildx build -f docker/deployexample/Dockerfile -t ghcr.io/cmahnke/windows-deployer/deployexample:latest . 
docker buildx build -f docker/windowsdeployer/Dockerfile -t ghcr.io/cmahnke/windows-deployer/windowsdeployer:latest .
