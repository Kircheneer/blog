Title: Linux Networking for the Cisco Admin
Date: 2021-05-22 16:00
Author: kirchnerl
Category: Networking
Tags: cisco, linux
Slug: linux-networking-for-the-cisco-admin
Status: published

If your job as a network administrator is anything like mine then
you often get pulled somewhat out of your comfort zone by supposed
network issues in end hosts. Some of the problems I've had to deal
with in this regard are the following:

- Servers with multiple network interfaces where a firewall rule
  was requested for the wrong interface
- Applications that had trouble correctly setting up their sockets
  and as a consequence don't listen on the ports they are supposed
  to listen on
- Host firewalls blocking traffic destined to the server

A handy cheat sheet for these operations can be found at the
[end](#cheat-sheet) of this post.

But helping server or application administrators is not the only 
motivation to learn at least a little bit on how networking
on Linux platforms works. Not only are there things like
[Cumulus Linux](https://www.nvidia.com/en-us/networking/ethernet-switching/cumulus-linux/)
or [FRRouting](https://frrouting.org/) (the latter of which is also
used by the former) which you might encounter running on actual
networking gear in the forwarding path between servers. If you want
to get into network automation you will undoubtedly encounter Linux.
You might for example want to run
[Ansible](https://docs.ansible.com/ansible/latest/network/index.html)
or [Netbox](https://netbox.readthedocs.io/en/stable/) / [Nautobot](https://www.networktocode.com/nautobot/)
both of which (currently) only run on Linux.

-----------------------------

First we will start looking into ways of getting information about
its networking configuration and operational status from a modern
Linux system. I will be using a fresh Ubuntu 20.04 install via
Vagrant - you can use the following Vagrantfile if you want to
follow along.

```Vagrantfile
# -*- mode: ruby -*-
# vi: set ft=ruby :
Vagrant.configure("2") do |config|
  config.vm.box = "generic/ubuntu2004"
end
```

*Note: By modern I mean a system that has
[iproute2](https://linux.die.net/man/8/ip) available instead of or
in addition to the mostly deprecated
[ifconfig](https://linux.die.net/man/8/ifconfig).*
 
## Collecting basic operational networking data with `ip`

One of the first things I learned on Cisco gear was
`show ip interface brief` to output basic information about any
layer 3 interfaces. The more or less equivalent command from the
`iproute2` command suite would be `ip -brief address show`. The
Ubuntu VM I'm using currently only has one interface facing my
hypervisor as well as one loopback interface so the output is
quite short for now.

```bash
$ ip -brief address show
lo               UNKNOWN        127.0.0.1/8
eth0             UP             10.0.2.15/24 fe80::a00:27ff:fe05:8f3d/64
``` 

As you can see the two aforementioned interfaces are present.
Furthermore, you can see their operational status (with lo being
`UNKNOWN` as it is a loopback interface) as well as any IP
addresses configured on those devices.

Of course, most people don't type `show ip interface brief` on
Cisco gear - I myself shorten that to `sh ip int brief` (which
is still more characters than really necessary). Similar to that,
I use `ip a` on Linux devices. As you can see you can both shorten
the commands and omit the `show` as it is the default behavior.

Using `ip -s address` (with '-s' standing for 'statistics' and
no '-br' for 'brief') you get the the output of `sh ip int brief`
interspersed with the some of the output of `show interface`
(namely the statistics):

```bash
$ ip -s address
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    RX: bytes  packets  errors  dropped overrun mcast
    3640       44       0       0       0       0
    TX: bytes  packets  errors  dropped carrier collsns
    3640       44       0       0       0       0
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000
    link/ether 08:00:27:05:8f:3d brd ff:ff:ff:ff:ff:ff
    inet 10.0.2.15/24 brd 10.0.2.255 scope global dynamic eth0
       valid_lft 79238sec preferred_lft 79238sec
    inet6 fe80::a00:27ff:fe05:8f3d/64 scope link
       valid_lft forever preferred_lft forever
    RX: bytes  packets  errors  dropped overrun mcast
    1108533    3680     0       0       0       0
    TX: bytes  packets  errors  dropped carrier collsns
    220015     2047     0       0       0       0
```

Another commonly used command on Cisco devices would
be `show ip route`. By now you can probably tell yourself
what th equivalent for the `iproute2` suite would be:
`ip route` with an optional `show` at the end (which is
the same words just in a different order):

```
$ ip route show
default via 10.0.2.2 dev eth0 proto dhcp src 10.0.2.15 metric 100
10.0.2.0/24 dev eth0 proto kernel scope link src 10.0.2.15
10.0.2.2 dev eth0 proto dhcp scope link src 10.0.2.15 metric 100
```

Now this is also comparatively boring as we only have
- A default route from DHCP
- A directly attached route for the network
- A host route for the interface itself
For comparison, here's a short excerpt from the Cisco
CLI containing the same kinds of routes (except for the
default route which is statically configured instead of
being issued by DHCP).

```
Switch#show ip route
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       o - ODR, P - periodic downloaded static route, H - NHRP, l - LISP
       a - application route
       + - replicated route, % - next hop override

Gateway of last resort is 192.168.2.1 to network 0.0.0.0

S*    0.0.0.0/0 [1/0] via 192.168.2.1
      192.168.2.0/24 is variably subnetted, 2 subnets, 2 masks
C        192.168.2.0/24 is directly connected, GigabitEthernet0/0
L        192.168.2.100/32 is directly connected, GigabitEthernet0/0
```

Finally there is `ip neigh` (equivalent to `show ip arp`) available
to query the ARP table of the Linux host:

```bash
$ ip neigh show
10.0.2.2 dev eth0 lladdr 52:54:00:12:35:02 REACHABLE 
```

With these simple commands you can already a lot of common
networking issues on Linux systems I have encountered:
- Wrongly configured subnet masks
- Missing (default) routes 
- Multiple interfaces with traffic using ones you didn't expect
  they would

If you take a look at `ip help` you can see there's a host
(pun intended) of other commands available for querying:

```bash
$ ip help
Usage: ip [ OPTIONS ] OBJECT { COMMAND | help }
       ip [ -force ] -batch filename
where  OBJECT := { link | address | addrlabel | route | rule | neigh | ntable |
                   tunnel | tuntap | maddress | mroute | mrule | monitor | xfrm |
                   netns | l2tp | fou | macsec | tcp_metrics | token | netconf | ila |
                   vrf | sr | nexthop }
       OPTIONS := { -V[ersion] | -s[tatistics] | -d[etails] | -r[esolve] |
                    -h[uman-readable] | -iec | -j[son] | -p[retty] |
                    -f[amily] { inet | inet6 | mpls | bridge | link } |
                    -4 | -6 | -I | -D | -M | -B | -0 |
                    -l[oops] { maximum-addr-flush-attempts } | -br[ief] |
                    -o[neline] | -t[imestamp] | -ts[hort] | -b[atch] [filename] |
                    -rc[vbuf] [size] | -n[etns] name | -N[umeric] | -a[ll] |
                    -c[olor]}
```

If you're interested in a good article on the topic of VRFs in
the Linux world, I recommend you go take a look at
[this article](https://www.dasblinkenlichten.com/working-with-linux-vrfs/)
by Jon Langemak.

## Using `jq` to query JSON output

Sometimes you might want to filter the output of the commands
to get exactly the data you need in the format you need it in.
Luckily, the `ip` command supports the outputting of 
structured data in the form of JSON by virtue of the `-j` flag:
```bash
$ ip -j route
[{"dst":"default","gateway":"10.0.2.2","dev":"eth0","protocol":"dhcp","prefsrc":"10.0.2.15","metric":100,"flags":[]},{"dst":"10.0.2.0/24","dev":"eth0","protocol":"kernel","scope":"link","prefsrc":"10.0.2.15","flags":[]},{"dst":"10.0.2.2","dev":"eth0","protocol":"dhcp","scope":"link","prefsrc":"10.0.2.15","metric":100,"flags":[]}]
```

That output is not really pretty, is it? Enter: `jq`.

*Note: If you're following along on a brand new VM
you will at this point have to install the jq tool.
In the Ubuntu machine you get by using the Vagrantfile
at the beginning of this post that is done by
`sudo apt install jq -y`.*

`jq` is a command line JSON processor. In its simplest
form, we can use it to format the data in a prettier way:

```bash
$ ip -j route | jq
[
  {
    "dst": "default",
    "gateway": "10.0.2.2",
    "dev": "eth0",
    "protocol": "dhcp",
    "prefsrc": "10.0.2.15",
    "metric": 100,
    "flags": []
  },
  {
    "dst": "10.0.2.0/24",
    "dev": "eth0",
    "protocol": "kernel",
    "scope": "link",
    "prefsrc": "10.0.2.15",
    "flags": []
  },
  {
    "dst": "10.0.2.2",
    "dev": "eth0",
    "protocol": "dhcp",
    "scope": "link",
    "prefsrc": "10.0.2.15",
    "metric": 100,
    "flags": []
  }
]
```

While nicely colored and formatted CLI output is a
nice-to-have goodie, `jq` really starts to shine
once you need to filter data you receive. Say you
want to find all interfaces that have transmitted
at least 100000 bytes of traffic and output their
names, you could use the following command to do
that:

```bash
$ ip -j -s address | jq '.[] | select(.stats64.rx.bytes > 100000) | .ifname'
"eth0"
```

I am aware that this example is somewhat
removed from what you might need in reality - I'm
merely using to show of some of what `jq` can do.
You could just as well use this command to find
interfaces with error counters to identify potential
issues with packet loss.

## Collecting application level data

When troubleshooting networking issues at any point
it's - in my opinion - always a good idea to start
at the bottom of the stack. Once you have verified
that the server has link status and appropriate
IP addresses as well as routes configured we can start
to verify if the fault lies with the application itself.
In order for any network communication to happen, a
socket has to have been opened on the correct TCP/UPD port.
The modern way of doing this is with the `ss` command
(make sure to run with `sudo` if you want the process names
to be output as well):

```bash
$ sudo ss -tulpen
Netid State  Recv-Q Send-Q Local Address:Port Peer Address:Port Process
udp   UNCONN 0      0      127.0.0.53%lo:53   0.0.0.0:*         users:(("systemd-resolve",pid=520,fd=12)) uid:101 ino:19780 sk:52 <->
udp   UNCONN 0      0      10.0.2.15%eth0:68  0.0.0.0:*         users:(("systemd-network",pid=379,fd=19)) uid:100 ino:23836 sk:53 <->
tcp   LISTEN 0      4096   127.0.0.53%lo:53   0.0.0.0:*         users:(("systemd-resolve",pid=520,fd=13)) uid:101 ino:19781 sk:54 <->
tcp   LISTEN 0      128    0.0.0.0:22         0.0.0.0:*         users:(("sshd",pid=1059,fd=3)) ino:24086 sk:55 <->
tcp   LISTEN 0      128    [::]:22            [::]:*            users:(("sshd",pid=1059,fd=4)) ino:24088 sk:56 v6only:1 <->
```

This is an overview of all the open sockets (read:
transport layer ports accepting traffic). You can also
get a list of open connections using `ss`:

```bash
$ Netid State Recv-Q Send-Q Local Address:Port Peer Address:Port Process
tcp     ESTAB 0      0      10.0.2.15:ssh      10.0.2.2:35294
```

You can for example use this output and match it up with
firewall logs or packet captures to see if clients
trying to establishing sessions are successful in doing so.

# Command mapping table <span id="cheat-sheet"><span>

Finally, I have compiled a small, cheat-sheet-esque table
mapping Cisco commands to `iproute2` commands (with no
attempt at covering all there is to cover):

| Cisco IOS/NXOS                    | `iproute2`               |
|-----------------------------------|--------------------------|
| `show ip interface brief`         | `ip -br address`         |
| `show interface eth1/1`           | `ip -s link show eth0`   |
| `show ip route`                   | `ip route`               |
| `show ip route 192.0.2.1`         | `ip route get 192.0.2.1` | 
| `show ip route | json`            | `ip -j route`            |
| `show ip arp`                     | `ip neigh`               |
| `show ip vrf`                     | `ip vrf`                 |
| `conf t`, `int eth1/1`, `shut`    | `ip link set eth0 down`  |
| `conf t`, `int eth1/1`, `no shut` | `ip link set eth0 up`    |