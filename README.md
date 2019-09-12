vctools
======

[![Status](https://travis-ci.org/mdechiaro/vctools.svg?branch=master)](https://travis-ci.org/mdechiaro/vctools)

[Overview](README.md#Overview)
[Install](README.md#Install)
[Create](README.md#Create)
[Boot](README.md#Boot)
[Contribute](README.md#contributing)
[Usage](README.md#usage)


# Overview

This is a Python module using pyvmomi which aims to simplify
command-line operations inside vCenter for linux sysadmins. Here is a
short list of what it can do:

  - Automate a new VM creation using yaml. This includes boot options.
  - Reconfigure VM hardware like networks, disks, CPU, and memory.
  - Query various information on objects within VMware.
  - Upload ISOs to remote datastores, mount, and unmount them on VMs.
  - Upgrade VM hardware

# Install:

## vctools
python 3.6 and pipenv

```
git clone https://www.github.com/mdechiaro/vctools
cd vctools
pipenv --python 3.6 && pipenv install
cp vctools/examples/vctoolsrc.yaml.example ~/.vctoolsrc.yaml
ln -s vctools/main.py ~/bin/vctools
```

If you wish to share this project with other users, then copy the file to
the root of the project and edit the group permissions appropriately.
```
cp vctools/examples/vctoolsrc.yaml.example vctools/vctoolsrc.yaml
```

## mkbootiso

All necessary steps to configure can be found inside `.travis.yml`.
Further config examples can be found [here](examples/api).

```
- genisoimage
- apache2 / httpd
- mod_wsgi
- flask
```

## cloud-init
This project needs to be installed onto the template which vctools will
then clone as the new virtual machine.

```
- cloud-init
- https://github.com/vmware/cloud-init-vmware-guestinfo
```

# Create

This program will merge a default "rc" config file and a server config
into a VM creation config. It will prompt the user for any missing info
that is required to create a VM, and then automate the build process
from start to finish. It can handle multiple configs at once and merge
them separately with the dotrc for complex configurations.

An example simplified vmconfig. This will prompt you for additional
information to complete the process. These values will override any set
inside inside `~/.vctoolsrc.yaml` or `/path/to/vctoolsrc.yaml`.

```
# hostname.yaml
vmconfig:
  name: hostname
```

These will be treated as default values unless overriden in the VM
creation config.

```
# ~/.vctoolsrc.yaml
vmconfig:
  numCPUs: 2
  memoryMB: 4096
  memoryHotAddEnabled: True
  cpuHotAddEnabled: True
  disks:
    0:
    - 50
    1:
    - 25
  folder: Linux Team
```

An example of vmconfig without prompts for fully unattended install.

```
# hostname.yaml
vmconfig:
  cluster: 1234_cluster_01
  cpuHotAddEnabled: true
  datacenter: Linux
  datastore: 1234_datastore_01
  disks:    # assign disks to specific scsis
    0:      # scsi
    - 50    # disk size in GB
    1:
    - 1500
  folder: Linux Team
  guestId: rhel7_64Guest
  memoryHotAddEnabled: true
  memoryMB: 4096
  name: hostname
  nics:
  - 1000_foo_network
  - 1001_bar_network
  numCPUs: 2
```

Any configs that you wish to be set as defaults should be added to
`~/.vctoolsrc.yaml` or `/path/to/vctools/vctoolsrc.yaml`, and then can
be overridden on a per server basis with user supplied configs. In
addition, any features that you do not need should be completely
omitted.

The creation process will output all configurations for the server in
yaml format for easy rebuilds in the future.

# Boot
If PXE/DHCP isn't an option for you, then look below at other options
available.

## mkbootiso

An Apache Flask API that allows for custom boot isos on a per server
basis. This iso will need to be uploaded to a remote datastore, and then
virtually mounted into the server cdrom drive. The iso will need to be
provided and extracted into a directory tree that vctools (apache) can
read and write. It is recommended to network install the OS onto the
system to keep the iso upload small.

### extract

For initial instructions, you can review the docstring documentation
[here](api/mkbootiso.py). Once the API is operational, then you can
refer to the docs by:

```
curl https://hostname.domain.com/api/mkbootiso
```

### example
An example addition to the yaml config:

```
# hostname.yaml
---
mkbootiso:
  ks: http://host.domain.com/ks.cfg
  options:
    gateway: 10.1.1.1
    hostname: hostname.domain.com
    ip: 10.1.1.10
    nameserver: 4.2.2.2
    netmask: 255.255.255.0
  source: /opt/isos/rhel7
```

A boot iso can also be created outside of vctools, using curl:

```
curl -i -k -H "Content-Type: application/json" -X POST \
    https://hostname.domain.com/api/mkbootiso \
    -d @- << EOF
        {
            "source" : "/opt/isos/rhel7",
            "ks" : "http://ks.domain.com/rhel7-ks.cfg",
            "options" : {
                "gateway" : "10.10.10.1",
                "hostname" : "hostname.domain.com",
                "ip" : "10.10.10.10",
                "nameserver" : "4.2.2.2",
                "netmask" : "255.255.255.0"
            },
            "output": "/tmp"
        }
EOF
```

## cloud-init
[Website](https://cloudinit.readthedocs.io/en/latest/)

Metadata and userdata can be inserted into the created virtual machine,
which can then be parsed by cloud-init.

### example
An example addition to the yaml config:

```
# hostname.yaml
---
metadata:
  local-hostname: hostname.domain.com
  network:
    version: 2
    ethernets:
      ens224:
        dhcp4: false
        addresses:
        - 10.1.1.10/24
        gateway4: 10.1.1.1
        nameservers:
          search:
          - domain.com
          addresses:
          - 4.2.2.2
```

# Contributing:

Pull requests are welcome. Travis CI will test for syntax errors, so it
is recommended that you run this code when making changes and before you
commit.

```
# type `pipenv shell` and run inside project directory
find . -not \( -name ".venv" -prune \) -name "*.py" -type f | xargs pylint --rcfile=.pylintrc
```

Here's a quick way to set it up in the Python intepreter and then you
can move freely around the interface. The commands dir() and getattr()
are very helpful.

```
from pyVmomi import vim
from vctools.auth import Auth
from vctools.query import Query
auth = Auth(<vcenter_host>)
auth.login()
Password:
query = Query()

You can create numerous containers like so:

virtual_machines = query.create_container(
    auth.session, auth.session.content.rootFolder, [vim.VirtualMachine], True
)

clusters = query.create_container(
    auth.session, auth.session.content.rootFolder, [vim.ComputeResource], True
)

vm_name = query.get_obj(virtual_machines.view, 'vm_name')

dir(vm_name)
```

# Usage:

## vctools
```
vcenter tools cli

    add          hardware to virtual machines.
    create       create virtual machines
    drs          cluster drs rules
    mount        iso onto cdrom
    query        information
    reconfig     virtual machine attributes and hardware
    umount       iso from cdrom
    upload       data to remote datastore
```

## add
```
help: vctools add -h
```

### add a network card
```
vctools add <vcenter> <name> --device nic  --network <network>
```

## create
```
help: vctools create -h
```

### create vm
```
vctools create <vcenter> <config> <configN>
```

### clone vm from template
```
vctools create <vcenter> <config> <configN> --template <template>
```
## drs
```
help: vctools drs -h
```

### add rule
```
vctools drs <vcenter> anti-affinity add <name> --vms <vm1 vm2...>
```
### delete rule
```
vctools drs <vcenter> anti-affinity delete <name>
```

## mount
```
help: vctools mount -h
```

### mount iso
```
vctools mount <vcenter> --name <server> --path <file.iso> --datastore <datastore>
```
## reconfig
```
help: vctools reconfig -h
```

### reconfigure memory and cpu
see VMware SDK [vim.vm.ConfigSpec](https://www.vmware.com/support/developer/vc-sdk/visdk41pubs/ApiReference/vim.vm.ConfigSpec.html) for all possible options
```
vctools reconfig <vcenter> <name> --cfgs memoryMB=<int>,numCPUs=<int>
```
### insert metadata, userdata, vendor data to vm for cloud-init
```
vctools reconfig <vcenter> <name> --extra-cfgs guestinfo.metadata=<gzip+base64> \
    guestinfo.metadata.encoding=gzip+base64
```
### convert vm to be a template
```
vctools reconfig <vcenter> <name> --markastemplate
```
### move vm to another folder
```
vctools reconfig <vcenter> <name> --folder <str>
```
### reconfigure a disk
The flag "disk-id" is the number associated with the name of the
disk on the VM that you want to grow, e.g. "Hard disk 1".
```
vctools reconfig <vcenter> <name> --device disk --disk-id <int> --sizeGB <int>
```
### reconfigure a network card
```
vctools reconfig <vcenter> <name> --device nic --nic-id <int> --network <network>
```
### upgrade vm hardware
```
vctools reconfig <vcenter> <name> --upgrade --scheduled
```

## umount
```
help: vctools umount -h
```

### umount iso
```
vctools umount <vcenter> --name name nameN
```

## upload
```
help: vctools upload -h
```

### upload iso to remote datastore
```
vctools upload vcenter --iso /local/path/to/file.iso \
    --dest /remote/path/to/iso/folder --datastore datastore \
    --datacenter datacenter
```
