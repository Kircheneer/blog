Title: Using suzieq with netsim-tools
Date: 2021-05-02 14:44
Author: kirchnerl
Category: Networking
Tags: suzieq, docker, ansible, vagrant, libvirt
Slug: using-suzieq-with-netsim-tools
Status: published

The following two tools had been on my "check-this-out" list for a couple
of weeks now:

- [Suzieq](https://github.com/netenglabs/suzieq): An observability
  framework/application for network devices
- [netsim-tools](https://github.com/ipspace/netsim-tools): A set of Python
  scripts and Ansible playbooks for to simplify the process of building
  virtualized network labs

The following blog post describes my experience with combining these two.

# Virtualizing network devices

In the past I have mostly used [GNS3](https://gns3.com/) for my virtual
network labbing purposes. While this works quite well, I was a little
annoyed having to set up the same basic configuration everytime:

1. SSH access
1. IP addresses on links between the devices
1. Routing protocols

[Ivan Pepelnjak](https://www.ipspace.net/Main_Page) probably thought
something along those lines as well when he created netsim-tools. I
started my foray into the project by contributing a little
[Ansible playbook](https://github.com/ipspace/netsim-tools/blob/master/install.libvirt)
that installs the project and its dependencies to a Ubuntu machine
because I try to keep my testing VMs as cattle in regards to the
"Pets vs. Cattle" analogy. You can use this playbook to install all of
the dependencies to use the tools on a Ubuntu system (shamelessly stolen
from the [docs](https://netsim-tools.readthedocs.io/en/latest/index.html)).

```bash
$ wget https://raw.githubusercontent.com/ipspace/netsim-tools/master/install.libvirt https://raw.githubusercontent.com/ipspace/netsim-tools/master/requirements.yml
$ ansible-playbook install.libvirt --ask-become -e /opt/netsim-tools
```

This default to installing to `/opt/netsim-tools` although that can be
customized.

## Overview of netsim-tools

Netsim-tools provides tools to perform the following tasks:

- Automate file creation based on a simple topology file for
  - Vagrantfile
  - Ansible inventory
- Deploy initial configuration with various optional features (e.g.
  basic routing protocol configuration) using Ansible
- Various other utilities for configuration management

Unfortunately, you still have to put in a little leg work yourself to
get the VMs from the vendors. Juniper, Cisco and Arista for example
all allow for downloads of virtual appliances, but only once you sign up
on their web sites. Take a look at Ethan Banks blog post on this topic
[here](https://ethancbanks.com/free-networking-lab-images-from-arista-cisco-nvidia-cumulus/).
He explains where to find free networking lab images.

My examples will use the NXOS 9000v for which you can
[download](https://software.cisco.com/download/home/286312239/type/282088129/release/9.3(7))
a Virtualbox based Vagrant box. In order to use that box with Vagrant
and Ivan's tools you have to convert the box to the libvirt provider with
`https://github.com/sciurus/vagrant-mutate`:

```bash
$ vagrant mutate file:///path/to/vagrant.box libvirt
```

You can now add the ready-to-use box.

## Using netsim-tools

A sample topology file might look like this:

```yaml
module: [ bgp, ospf ]

bgp:
  as: 65000
ospf:
  area: 0.0.0.0
defaults:
  device: nxos
nodes:
  - name: r1
  - name: r2
links:
  - r1-r2
```

This describes two connected Cisco NXOS with basic OSPF config to ensure
loopback interface reachability in order for a BGP session to be
established over those loopback interfaces.

The following command defaults to `./topology.yml` as the input and
generates the following files as its output:
- Vagrantfile
- hosts.yml (Ansible inventory)
- ansible.cfg

```bash
$ ./create-topology -g -i -c
Created provider configuration file: Vagrantfile
Created group_vars for nxos
Created host_vars for r1
Created host_vars for r2
Created minimized Ansible inventory hosts.yml
Created Ansible configuration file: ansible.cfg
```

The subsequent `vagrant up` creates all the machines in the topology
with the appropriate links. This takes a couple of minutes on my setup -
your mileage may vary.

## Debugging Vagrant / libvirt / vendor issues

If you experience any issues during `vagrant up`, you can use the
following steps to debug the installation process:

- List all the virtual machines created with libvirt with `virsh list`
- Console into any failing devices with `virsh console netsim-tools_r1`

I had one central problem which I found using this process:

Neither NXOS nor Junos liked my setup with a Ubuntu VM using an AMD
CPU. I had to set `domain.cpu_mode = "custom"` which sets
the `--cpu qemu64` flag for the qemu command that runs the VM. This
hinders performance but made all the machines run fine. This lead to
issues where the Junos machine wouldn't boot at all or the NXOS
machine was unable to save its running configuration to the startup
configuration. 

## Using Ansible with netsim-tools

After your VMs are all set up you can use Ansible to deploy the initial
configuration (including BGP and OSPF) to the virtual machines:

```bash
$ ansible-playbook initial-config.ansible
```

Once that's done you can SSH into one of the machines and take a look
at the routing protocol state:

```bash
$ vagrant ssh r1
[...]
r1# sh ip ospf neighbors
 OSPF Process ID 1 VRF default
 Total number of neighbors: 1
 Neighbor ID     Pri State            Up Time  Address         Interface
 10.0.0.2          1 FULL/ -          00:00:08 10.1.0.2        Eth1/1
r1# sh ip bgp neighbors | i "neighbor is"
BGP neighbor is 10.0.0.2, remote AS 65000, ibgp link, Peer index 3
r1# sh ip route
IP Route Table for VRF "default"
'*' denotes best ucast next-hop
'**' denotes best mcast next-hop
'[x/y]' denotes [preference/metric]
'%<string>' in via output denotes VRF <string>

10.0.0.1/32, ubest/mbest: 2/0, attached
    *via 10.0.0.1, Lo0, [0/0], 00:01:25, local
    *via 10.0.0.1, Lo0, [0/0], 00:01:25, direct
10.0.0.2/32, ubest/mbest: 1/0
    *via 10.1.0.2, Eth1/1, [110/41], 00:00:58, ospf-1, intra
10.1.0.0/30, ubest/mbest: 1/0, attached
    *via 10.1.0.1, Eth1/1, [0/0], 00:01:23, direct
10.1.0.1/32, ubest/mbest: 1/0, attached
    *via 10.1.0.1, Eth1/1, [0/0], 00:01:23, local
```

To finish up, make sure to run the following command to grab
the Ansible inventory in a format we can input to Suzieq:

```bash
$ ansible-playbook --list > inventory.json
```

# Using Suzieq for central observability

In this chapter we will take a look at using Suzieq to get a little
insight into our little network.

To summarize the previous chapter, you should now have the following:

- Two Cisco NXOS VMs running under libvirt using Vagrant
- OSPF and BGP setup between them
- An Ansible inventory representation in a `inventory.json` file

You can either use Docker to run suzieq or install the Python package
from Pypi (see getting started section of the
[docs](https://suzieq.readthedocs.io/en/latest/getting_started/)). For
the purposes of this post I will use the Python package:

```bash
$ mkdir suzieq && cd suzieq
$ python -m venv venv
$ source venv/bin/activate
$ pip install suzieq
```

Now copy the `inventory.json` file into the `suzieq` folder.
