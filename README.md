vctools
======

version: 0.1.3

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
  - python-pip
  - python-requests
  - python-yaml
  - pyVmomi


Quick Install (on Linux Mint 17.2):

    sudo apt-get install python-yaml python-pip
    sudo pip install pyVmomi
    cp .vctoolsrc.yaml ~/

VM Creation:

This program will merge a dotrc config (.vctoolsrc.yaml) and a user
supplied VM build config (sample.yaml) into a VM creation config. It
will prompt the user for any necessary missing info, and then automate
the build process from start to finish.  

It is capable of creating a boot ISO per server (mkbootiso) for
situations when DHCP or PXE booting is not an option. It can also
upload, mount, and power on the VM after its creation making the process
completely automated. It can handle multiple configs at once and merge
them separately with the dotrc for complex configurations.  

A minimal yaml config (you will be prompted for other information):

    ---
    vmconfig:
      name: server
      guestId: rhel7_64Guest
      annotation: 'This will show up under Notes'
      disks:
      - 30
      - 50
      nics:
      - vlan_1234_linux_vlan
      mkbootiso:
      template: rhel7
      options:
        hostname: 'server.domain.com'
        ip: '10.1.1.10'
        gateway: '10.1.1.1'

A complete, no prompt config looks like this:

    ---
    vmconfig:
      cluster: 1234_lin_tst_01
      folder: 'Linux Team'
      datastore: T2_1234_Test_Datastore
      name: server
      guestId: rhel7_64Guest
      numCPUs: 1
      memoryMB: 4096
      memoryHotAddEnabled: True
      cpuHotAddEnabled: True
      annotation: 'This will show up under Notes'
      disks:
      - 30
      - 50
      nics:
      - vlan_1234_linux_vlan
      mkbootiso:
        source: '/mnt/isos/rhel7'
        ks: 'http://ks.domain.com/rhel7-ks.cfg'
        options:
          hostname: 'server.domain.com'
          ip: '10.1.1.10'
          netmask: '255.255.255.0'
          gateway: '10.1.1.1'
          nameserver: '4.2.2.2'
          net.ifnames: '0'
          biosdevname: '0'
      upload:
      mount:
      power: 'on'

Any configs that you wish to be set as defaults should be added to
.vctoolsrc.yaml, and then can be overridden on a per server basis with
user supplied configs.

The creation process will output all configurations for the server in
YaML format for easy rebuilds in the future.  Committing these files to
your favorite version control system is recommended.

Command Line (Argparse) Usage:

Create a New VM:

    ./vctools.py create vcenter sample.yaml sample2.yaml sampleN.yaml

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

Contributing:

Pull requests are welcome.  Please follow PEP 8, and pylint is
recommended for ensuring the code follows those standards.

Thanks:

A special thanks goes out to VMware Onyx, as well as my colleagues,
which allowed me to make this code possible.
