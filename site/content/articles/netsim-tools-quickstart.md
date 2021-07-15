Title: A quick introduction to netsim-tools
Date: 2021-05-13 14:44
Author: kirchnerl
Category: Networking
Tags: ansible, vagrant, libvirt, cisco, linux
Slug: netsim-tools-quickstart
Status: published

The somewhat newly released [netsim-tools](https://github.com/ipspace/netsim-tools)
by [Ivan Pepelnjak](https://www.ipspace.net/Main_Page) has been on my "check-this-out" list for a couple of weeks
now. It contains a set of tools to simplify the process of creating virtual network
labs. In the following sections I will lay out how to quickly get started with
labbing on Cisco NXOS 9000v or Cumulus Linux devices using netsim-tools.

*Note: Following the 0.8 release of netsim-tools this post received an update to
use the pip-way of installing the tools.*

# Virtualizing network devices

In the past I have mostly used [GNS3](https://gns3.com/) for my virtual
network labbing purposes. While this works quite well, I was a little
annoyed having to set up the same basic configuration everytime:

1. SSH access
1. IP addresses on links between the devices
1. Routing protocols

Ivan probably thought something along those lines as well when he created netsim-tools.

## Vagrantfile for netsim-tools

I'm using Vagrant for creating my development environment here. For the
purposes of this blog post I will assume that you already have Vagrant
installed. Otherwise, just take a look at the
[docs](https://www.vagrantup.com/docs/installation).

The first step will be creating a Vagrantfile for the test VM. I'm running
Virtualbox as the Vagrant provider from a Windows 10 machine, but thanks
to the power of Vagrant these instructions should work on any OS.

*Note: A prerequisite is a host OS supporting nested virtualization, because
we will be using KVM inside of the Vagrant provisioned Ubuntu VM.*

*Note: While I wrote the old version of this Vagrantfile myself, credit for
the update to the pip-way of installing in this one goes to Ivan!*

```Vagrantfile
Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/focal64"

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "8192"
    vb.cpus = 4
    vb.customize ['modifyvm', :id, '--nested-hw-virt', 'on']
  end

  config.vm.provision "shell", inline: <<-SHELL
    apt-get update
    apt-get install -y python3-pip
    pip3 install netsim-tools
    netlab install -y ubuntu ansible libvirt
    usermod -aG libvirt vagrant
  SHELL
end
```

Make sure to adjust the `vb.memory` and `vg.cpus` settings to your needs.
Virtualbox starts throwing warnings whenever you have a VM consuming
\>=75% of the hypervisor hosts memory capacity.

Place this file in a directory on your host OS and then run `vagrant up`.
This will do the following things (and therefore might take a little while):

1. Download and boot a Ubuntu 20.04 Vagrant box
1. Enable nested virtualization in the Virtualbox settings of the VM
1. Install pip inside of the box
1. Add the vagrant user to the libvirt group so we can use libvirt without `sudo`
1. Install `netlab` to the system python interpreter from PyPI

*Note: We are using the system Python interpreter here instead of a
virtual Python environment. Normally, this would be a bad idea, but because 
this is a throwaway VM we can remove that complexity.*

Once the machine successfully comes up, you can SSH into it with
`vagrant ssh`. All subsequent command line excerpts are from the VM.

## Readying the NXOS 9000v box for use with netsim-tools

*The following section describes how to ready a Cisco NXOS
9000v box for virtual labbing. If you aren't set on a vendor
I recommend you check out
[Cumulus Linux](https://www.nvidia.com/en-us/networking/ethernet-switching/cumulus-linux/)
as they provide the most-hassle free Vagrant box experience
(it's available on the public Vagrant registry!). Just use the
OS "cumulus" inside of the topology file further down.*

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
He explains where to find free networking lab images. In the coming steps
I will assume that you have downloaded a copy of a NXOS 9000v Vagrant box
and put that file into the directory containing the Vagrantfile of the
Ubuntu VM (Vagrant automatically syncs that directory to `/vagrant` in the
guest operating system).

*Note: While netsim-tools supports a Virtualbox backend for some of the VMs
(including the NXOS 9000v) I will, for the purposes of this blog post,
be using a libvirt backend.*

In order to use that box with Vagrant and Ivan's tools you have to convert
the downloaded box to the libvirt provider with
`https://github.com/sciurus/vagrant-mutate` and repackage it with the correct
version and name for netsim-tools to pick up. Don't worry if the mutate command
takes a while - it has to copy the contents of the entire box file at some point.
The `mv` command is used to rename the box to the name at which netsim-tools
expects the box to be.

*Note: You can skip the step of copying into `/tmp` and have `vagrant mutate` read from
`/vagrant` directly - I opted not to do this because my `vagrant mutate` command
always seemed to stall out at 99% when reading diretly from the shared folder.*

```bash
$ ls /vagrant
nexus9300v.9.3.7.box
$ vagrant plugin install vagrant-mutate
$ cp /vagrant/nexus9300v.9.3.7.box /tmp
$ vagrant mutate file:///tmp/nexus9300v.9.3.7.box libvirt
$ mv ~/.vagrant.d/boxes/nexus9300v.9.3.7/ ~/.vagrant.d/boxes/cisco-VAGRANTSLASH-nexus9300v
```

At this point you could start using the box manually, but we will be leveraging
netsim-tools to do most of the hard lifting for us. You might also want to copy
the box folder `~/.vagrant.d/boxes/cisco-VAGRANTSLASH-nexus9300v` back to
`/vagrant` in case you ever need to `vagrant destroy` you Ubuntu VM.

## Using netsim-tools

Netsim-tools uses a YAML files to describe topologies. These include
the actual nodes to be provisioned, links between the nodes,
any modules to be deployed onto the nodes and finally configuration
for those modules.

Copy the content of the following topology file into any folder inside of
the box, for the purposes of this tutorial I will be using the home folder.

*Note: As mentioned above, if you skipped the NXOS 9000v part you can use
"cumulus" as the device type here and it will just work without
any further preparation.*

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

The `netlab create` python script defaults to `./topology.yml` as the
input and generates the following files as its output:
- Vagrantfile
- hosts.yml (Ansible inventory)
- ansible.cfg

```bash
$ ls
topology.yml
$ netlab create
Created provider configuration file: Vagrantfile
Created group_vars for nxos
Created host_vars for r1
Created host_vars for r2
Created minimized Ansible inventory hosts.yml
Created Ansible configuration file: ansible.cfg
```

Make sure to take a look into the generated Vagrantfile. All the configuration
we entered manually when we instantiated the Ubuntu VM we are currently
operating in have been auto-generated for us by netsim-tools.

A subsequent `vagrant up` creates all the machines in the topology
with the appropriate links. This takes a couple of minutes on my setup;
your mileage may vary.

## Debugging Vagrant / libvirt / vendor issues

If you experience any issues during `vagrant up`, you can use the
following steps to debug the installation process:

- List all the virtual machines created with libvirt with `virsh list`
- Console into any failing devices with `virsh console netsim-tools_r1`

I had one central problem which I found using this process:

Neither NXOS nor Junos liked my setup with a Ubuntu VM using an AMD
CPU. This lead to issues where the Junos machine wouldn't boot at
all or the NXOS machine was unable to save its running configuration
to the startup configuration.I had to set `domain.cpu_mode = "custom"`
on most VMs which sets the `--cpu qemu64` flag for the qemu command
that runs the VM. This hinders performance but made all the machines
run fine.  With release 0.6.2 of netsim-tools this should be resolved,
as the `cpu_mode` parameter is automatically set to `custom`whenever
an AMD CPU is used.

## Using Ansible with netsim-tools

After your VMs are all set up you can use Ansible to deploy the initial
configuration (including BGP and OSPF) to the virtual machines. The following
basically command acts as a frontend to `ansible-playbook` running a playbook
to deploy a specified set of commands in order to configure the configuration
described in the topology file:

```bash
$ netlab initial
```

Once that's done you can SSH into one of the machines and take a look
at the routing protocol state. `netlab` also provides a handy shorthand for
this:

```
$ netlab connect r1
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

As you can see at this point the routing protocol neighborships
have been successfully established.

Apart from deploying pre-baked initial configurations we can also use the
`netlab config` command to deploy our own custom configuration templates
to the devices as follows:

```
$ echo "no feature telnet" > config.j2
$ netlab config config.j2
```

Note that all this passes every argument except for the first one verbatim
to `ansible-playbook`, which allows you to control its behavior. You can of
course get more complex with those templates rather than merely disabling telnet.

## Conclusion

In this blog post I demonstrated how to use Vagrant, netsim-tools and Linux
to build a virtual network lab. I personally feel like the instant Ansible
integration and batteries-includedness regarding boilerplate routing protocol
configuration are useful enough for me to forgive the lack of a shiny graphical
user interface guiding me through the process. Finally, I'd like to thank Ivan
Pepelnjak for his patience in accepting my many pull requests over the course
of my exploration into the world of netsim-tools.

If you want to find out more about netsim-tools, make sure to visit Ivan's
[blog](https://blog.ipspace.net/series/netsim-tools.html) about it. Thanks
for reading!
