Title: Docker alongside GNS3 on a Windows / AMD system
Date: 2020-11-23 19:49
Author: kirchnerl
Category: Networking
Tags: GNS3, Linux, Networking
Slug: docker-alongside-gns3-on-a-windows-amd-system
Status: published

When trying to run [Docker](https://www.docker.com/) and [GNS3](https://gns3.com/) on the same Windows system with an
AMD processor I was faced with the following challenges:

- [Docker for Desktop](https://docs.docker.com/docker-for-windows/install/) on Windows requires Hyper-V or WSL2,
  the latter in turn requires Hyper-V
- Hyper-V on AMD processors only supports nested virtualization as of
  [2020](https://techcommunity.microsoft.com/t5/virtualization/amd-nested-virtualization-support/ba-p/1434841)
  (in fact the official docs still say that
  "[nesting is currently Intel-only](https://docs.microsoft.com/en-us/virtualization/hyper-v-on-windows/user-guide/nested-virtualization)")
- Hyper-V officially supports only Hyper-V itself for netsed virtualization, therefore rendering it useless for
  running GNS3

After being fed up with running GNS3 on a separate physical Linux machine I tried to come up with an actual solution to
the problem. Seeing as I was already running Docker and GNS3 on an Ubuntu device I figured it should be possible to expose both of that to a Windows host through a (non Hyper-V!) VM.

## Installing GNS3 in a Ubuntu VM

*You need a working Ubuntu VM with a network interface bridged to the internet-facing interface of the host system to
follow along. Seeing as there are already lots of good tutorials on virtualization and the installation of Ubuntu
I won't cover this here. Free options are for example [VirtualBox](https://www.virtualbox.org/) or
[VMWare Workstation Player](https://www.vmware.com/products/workstation-player/workstation-player-evaluation.html)
(assuming you use it non-commercially).*

First off, make sure your VM is able to actually perform nested virtualization, as without it, this whole exercise
would be quite pointless.

```bash
$ kvm-ok
INFO: /dev/kvm exists
KVM acceleration can be used
```

The GNS3 [documentation](https://docs.gns3.com/docs/getting-started/installation/linux/) for installing it on a
Ubuntu-based distro is straight-forward. One thing I found was missing there was the daemonization of GNS3. Fortunately
enough they provide a Systemd service file
[here](https://raw.githubusercontent.com/GNS3/gns3-server/master/init/gns3.service.systemd). The following steps
configure the GNS3 daemon:

```bash
$ cd /etc/systemd/system
$ sudo wget https://raw.githubusercontent.com/GNS3/gns3-server/master/init/gns3.service.systemd
$ sudo mv gns3.service.systemd gns3.service
$ sudo useradd gns3
$ sudo usermod -aG ubridge gns3
$ sudo usermod -aG libvirt gns3 
$ sudo usermod -aG kvm gns3
$ sudo usermod -aG wireshark gns3
$ sudo usermod -aG docker gns3
$ sudo sed -i 's/\/var\/run\/run/' gns3.service
```

The last line fixes the fact that `/var/run` symlinks to `/run` on newer Ubuntu distributions. Start and enable the
service to run on startup and check on its status. If you the `Active: active (running)` then everything went well.

```bash
$ sudo systemctl start gns3
$ sudo systemctl enable gns3
$ sudo systemctl status gns3
● gns3.service - GNS3 server
    Loaded: loaded (/etc/systemd/system/gns3.service; enabled; vendor preset: enabled)
    Active: active (running) since Mon 2020-11-23 20:05:39 CET; 18s ago
[...]
```

Finally, either make sure that the host firewall is inactive or open the port in order to be able to access the GNS3
server from your Windows host:

```bash
$ sudo ufw status
 Status: inactive
# OR
$ sudo ufw allow 80
```

The last remaining step is to configure your GNS3 to use the server as the primary server. To check on how to do that,
take a look [here](https://docs.gns3.com/docs/getting-started/installation/one-server-multiple-clients/).

## Exposing Docker in a Ubuntu VM

***Disclaimer*****:** *The below steps expose an unauthenticated and unencrypted HTTP Docker daemon to the network.
Do not do this in a production environment or really anywhere that isn't on your home network. To find out how to
secure the Docker daemon, take a look* [*here*](https://docs.docker.com/engine/security/https/)*.*

If you haven't already installed Docker during the course of the GNS3 installation, take a look at how to install
Docker on a Ubuntu system [here](https://docs.docker.com/engine/install/ubuntu/). Out of the box the Docker daemon
runs locally on a [Unix socket](https://man7.org/linux/man-pages/man7/unix.7.html), walled of from the network. Because
we want to access it from our Windows host (which is reachable only through the network interface), we need to change
this. Systemd provides a mechanism for editing the service files without changing the original service file. This is
neat, because it ensures that the configuration properly persists through updates of the Docker packages.

Use the following commands to automatically create a `gns3.service.d` directory and `override.conf` with a
configuration that exposes the Docker daemon on port TCP/4243 of the VM (as demonstrated above make sure the firewall
configuration matches this). If you want to use Docker containers within GNS3 it is vital that you keep the Unix socket
configuration next to the TCP configuration, otherwise the GNS3 daemon will find itself unable to talk to the Docker
daemon.

```bash
$ sudo systemctl edit docker.service /etc/systemd/system/docker.service
## Enter following content into file
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd -H fd:// -H tcp://0.0.0.0:4243
```

You can also verify if your changes the service file were applied properly:

```
$ sudo systemctl cat docker
/lib/systemd/system/docker.service
[...]
# /etc/systemd/system/docker.service.d/override.conf
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd -H fd:// -H tcp://0.0.0.0:4243
```

Finishing up, we need to reload the service files and then restart the service.

``` {.wp-block-preformatted}
$ sudo systemctl daemon-reload
$ sudo systemctl restart docker
```

Your Docker daemon should now be up and running:

```
$ netstat -tpln | grep 4243
tcp6       0      0 :::4243                 :::*                    LISTEN      -
```

## Docker configuration on the Windows host

*If you don't mind installing the Docker daemon (even though you won't run it) as well as* `docker.exe` *and*
`docker-compose.exe` *on your Windows system you can simply use the*
[*official installer*](https://docs.docker.com/docker-for-windows/)*. Otherwise you can grab the newest release from*
[*here*](https://github.com/docker/cli)*.*

In order to configure your newly aquired Docker CLI to use the remote Docker daemon, you can either set the environment
variable `DOCKER_HOST` to the Ubuntu VM (e.g. `tcp://192.168.0.100:4243`), use `docker -H tcp://192.178.0.100:4243 ...`
or use the[configuration file](https://docs.microsoft.com/en-us/virtualization/windowscontainers/manage-docker/configure-docker-daemon).
With either of these options configured properly you should now be able to use the Docker (or docker-compose)
CLI from your Windows host:

```powershell
PS> docker run hello-world
 Hello from Docker!
 This message shows that your installation appears to be working correctly.
 To generate this message, Docker took the following steps:
 The Docker client contacted the Docker daemon.
 The Docker daemon pulled the "hello-world" image from the Docker Hub.
 (amd64)
 The Docker daemon created a new container from that image which runs the
 executable that produces the output you are currently reading.
 The Docker daemon streamed that output to the Docker client, which sent it
 to your terminal. 
 To try something more ambitious, you can run an Ubuntu container with:
  $ docker run -it ubuntu bash
 Share images, automate workflows, and more with a free Docker ID:
  https://hub.docker.com/
 For more examples and ideas, visit:
  https://docs.docker.com/get-started/
```
