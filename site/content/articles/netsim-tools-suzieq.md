Title: Using suzieq with netsim-tools
Date: 2021-05-02 14:44
Author: kirchnerl
Category: Networking
Tags: suzieq, docker, ansible
Slug: using-suzieq-with-netsim-tools
Status: draft

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
the dependencies to use the tools (tested on a Ubuntu 20.04 system).

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
on their web sites. In the case of Arista unfortunately my account is
still not approved after about a week of waiting. I followed the instructions
[here](https://github.com/mweisel/cisco-nxos9kv-vagrant-libvirt) in order
to create a Nexus 9000V Vagrant box before Dinesh Dutt of suzieq
told me there was a Vagrant box available for download from Cisco. In
order to use that box with Vagrant and Ivan's tools you have to convert
the box to the libvirt provider with
`https://github.com/sciurus/vagrant-mutate`.

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

This deploys two connected Cisco NXOS with basic OSPF config to ensure
loopback interface reachability in order for a BGP session to be
established over those loopback interfaces.