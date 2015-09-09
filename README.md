vctools
======


This is a Python module using pyVmomi which aims to simplify
command-line operations inside vCenter for Linux sysadmins. The current
state of this project is beta, and so far it can do the following:

  - Build a new VM using a yaml config
  - Query various information useful for building new VMs, such as
    datastores, networks, folders.
  - Upload local ISOs to remote datastores
  - Mount and Unmount ISOs
  - Interactive Wizard (POC)

It also supports a .vctoolsrc file using ConfigParser, which will allow
you override argparse options with common values for each command, and
allows for shorter command-line arguments. Put this file in your $HOME.

Dependencies:
  - Python 2.6+
  - python-argparse
  - python-configparser
  - python-pip
  - python-requests
  - python-yaml
  - pyVmomi


Quick Install (on Linux Mint 17.2):

    sudo apt-get install python-yaml python-configparser python-pip
    sudo pip install pyVmomi
    cp .vctoolsrc ~/

Usage:

Create a New VM:

    ./vctools.py create vcenter sample.yaml

Mount an ISO:

    ./vctools.py mount vcenter --name server --path /path/to/file.iso \
      --datastore datastore


Query Datastore Info:

    ./vctools.py query vcenter --cluster cluster --datastores

Reconfig Parameters

    ./vctools.py reconfig vcenter --params key1=value1,key2=value2 \
      --name hostname

    Parameters can be mostly any key value option listed under the
    ConfigSpec class inside the VMWare SDK.

    The format is key=value, and multiple options can be set by
    separating with a comma. For example, use "numCPUs=2,memoryMB=8192"
    to change the memory and CPU allocation on a VM.

Unmount an ISO:

    ./vctools.py umount vcenter --name server

Upload ISO to Datastore:

    ./vctools.py upload vcenter --iso /local/path/to/file.iso \
      --dest /remote/path/to/iso/folder --datastore datastore \
      --datacenter datacenter
