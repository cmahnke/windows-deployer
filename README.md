Windows Deployer
================

# Introduction

This collection of Docker images can be used to deploy an installer on a Windows machine behind a VPN gateway from a Linux / MacOS machine. This should also include a GitHub / GitLab runner.

The tool has been tested agains Windows 11 ARM, but should also work with Windows 10 on x86-64 / AMD64.

## Status
* Modules
    * `fileprovider` fails on multiple invocations
    * `windowsdeployer` needs to be tested
* Documentation isn't finished yet

## Known Issues
* Multiple invocations of `fileprovider` doesn't work yet, just start a new container.
* Setting the debug flag on `/etc/vpnc/vpnc-script` isn't reverted, just start a new container.

## Possible improvements / features
* Add a configuration file
* `vpnconnect`: Certificate based VPN login
* `windowsdeployer`:
    * Set the Windows shell to installed programm

## Features

# Building

The images depend on each other, make sure to build them in the order shown here.
But they are also build by GitHub, so there should be no need to build them, if you're not planning to change / improve them.

## MSI Tools

```
docker buildx build -f docker/msitools/Dockerfile -t ghcr.io/cmahnke/windows-deployer/msitools:latest .
```

## VPN Connector

```
docker buildx build -f docker/vpnconnect/Dockerfile -t ghcr.io/cmahnke/windows-deployer/vpnconnect:latest .
```

### File Provider

```
docker buildx build -f docker/fileprovider/Dockerfile -t ghcr.io/cmahnke/windows-deployer/fileprovider:latest .
```

### Windows Deployer

```
docker buildx build -f docker/windowsdeployer/Dockerfile -t ghcr.io/cmahnke/windows-deployer/windowsdeployer:latest .
```

### Deploy Example

```
docker buildx build -f docker/deployexample/Dockerfile -t ghcr.io/cmahnke/windows-deployer/deployexample:latest . 
```

# Usage

The final image `ghcr.io/cmahnke/windows-deployer/windowsdeployer:latest` contains all modules of the different images:
* `windowsdeployer`: Runs an installer via WMI
* `fileprovider`: Provides a directory via SMB
* `vpnconnect`: Connects to a Cisco Anyconnect VPN service
* `verify`: Checks if file service can be reached

Each subcommand has a `-h` (help) options, use it to get all implemented options. It's possible to pass some options from one module to another using Python templating. Just put variables of functions in curly brackets (`{`, `}`).

The folowing methods and varibles are available:
* `user()`: Generate a username
* `passwd()`: Generate a password
* `filename()`: Get the file from a path
* `mod`: Reference to other modules, beware that this incluudes all modules not only the used ones.

## Chaining commands

The easiest way to keep the list of arguments short is to just reuse the administartive account of the target machine of the target machine or the file provider like this:

```
/opt/entrypoint/run.py -v fileprovider -u 'Adminstrator' -p 'Password' windowsdeployer -p '{opt.fileprovider.args.password}' -t 10.10.0.1 -f setup.exe
```

# Running single images

These examples demontrate how to use each image individualy. This is mainly used for testing purposes.

## VPN Connect (`vpnconnect`)

The VPN connect utility uses the Cisco Any Connect protocoll by default.

You need to start docker with `--cap-add NET_ADMIN` and `--device /dev/net/tun`.

```
docker run -it --cap-add NET_ADMIN --device /dev/net/tun ghcr.io/cmahnke/windows-deployer/vpnconnect
```

```
/opt/entrypoint/run.py -v vpnconnect -u username -p password -s vpn.provider.com
```

## File provider (`fileprovider`)

```
docker run -it ghcr.io/cmahnke/windows-deployer/fileprovider
```

```
/opt/entrypoint/run.py -v fileprovider -u '{user()}' -p '{passwd()}'
```

### Verifier

The verifier is part of the `fileprovider` image

```
/opt/entrypoint/run.py -v verify -a 0.0.0.0 -s deployer
```

### Combining File and verifier
```
/opt/entrypoint/run.py -v fileprovider -u '{user()}' -p '{passwd()}' verify -u '{mod.fileprovider.args.user}' -p '{mod.fileprovider.args.password}' -a '{mod.fileprovider.args.address}' -s deployment
```

## Windows Deployer (`windowsdeployer`)

```
docker run -it --cap-add NET_ADMIN --device /dev/net/tun ghcr.io/cmahnke/windows-deployer/windowsdeployer
```

```
/opt/entrypoint/run.py -v windowsdeployer
```

# Development

For local development you need to install the following Python modules:
* `impacket`
* `smbprotocol`
* `ifaddr`

# Credits

This tool either uses or was inspired by the following projects:

* Inspiration for Docker based VPN: [`docker-vpn`](https://github.com/ethack/docker-vpn)
* OpenConnect VPN client: [OpenConnect](https://www.infradead.org/openconnect/)
* VPN Slice Script: [`vpn-sclice`](https://github.com/dlenski/vpn-slice)
* Python Network interface library: [`ifaddr`](https://github.com/pydron/ifaddr)
* Samba SMB Fileserver: [Samba](https://www.samba.org/)
* Python SMB client: [`smbprotocol`](https://github.com/jborean93/smbprotocol)
* Python based WMI executer: [`impacket`](https://github.com/fortra/impacket)
* Gnome MSI tools: [`msitools`](https://gitlab.gnome.org/GNOME/msitools)
