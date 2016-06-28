vctools
======

This is a Python module using pyVmomi which aims to simplify
command-line operations inside vCenter for Linux sysadmins. The current
state of this project is beta, and so far it can do the following:

  - Completely automate a new VM creation from start to finish. This
    includes creating a boot ISO if your environment does not support DHCP.
  - Reconfigure VM hardware like networks, disks, CPU, and memory
  - Query various information on VMs
  - Upload ISOs to remote datastores, and mount and unmount them on VMs.

Dependencies:
  - Python 2.7+
  - python-argparse
  - python-pip
  - python-requests
  - python-yaml
  - pyVmomi

Quick Install (on Linux Mint 17.2):

    sudo apt-get install python-yaml python-pip
    sudo pip install pyVmomi==5.5.0-2014.1.1
    cp .vctoolsrc.yaml.example ~/.vctoolsrc.yaml

VM Creation:

This program will merge a default config (.vctoolsrc.yaml) and a server
config (sample.yaml) into a VM creation config. It will prompt the user
for any missing info that is required to create a VM, and then automate
the build process from start to finish.

It is capable of creating a boot ISO per server (mkbootiso) for
situations when DHCP or PXE booting is not an option. It can also
upload, mount, and power on the VM after its creation making the process
completely automated. It can handle multiple configs at once and merge
them separately with the dotrc for complex configurations.

An example yaml config:

    mkbootiso:
      ks: http://host.domain.com/ks.cfg
      options:
        biosdevname: '0'
        gateway: 10.1.1.1
        hostname: hostname.domain.com
        ip: 10.1.1.10
        nameserver: 4.2.2.2
        net.ifnames: '0'
        netmask: 255.255.255.0
      source: /opt/isos/rhel7
    vmconfig:
      cluster: 1234_cluster_01
      cpuHotAddEnabled: true
      datacenter: Linux
      datastore: 1234_datastore_01
      disks:
      - 50
      - 1500
      folder: Linux Team
      guestId: rhel7_64Guest
      memoryHotAddEnabled: true
      memoryMB: 4096
      name: hostname
      nics:
      - 1000_foo_network
      - 1001_bar_network
      numCPUs: 1


Any configs that you wish to be set as defaults should be added to
.vctoolsrc.yaml, and then can be overridden on a per server basis with
user supplied configs. In addition, any features that you do not need
(mkbootiso) should be omitted.

The creation process will output all configurations for the server in
YaML format for easy rebuilds in the future. Committing these files to
your favorite version control system is recommended.

Command Line (Argparse) Usage:

Create a New VM:

    vctools.py create vcenter sample.yaml sample2.yaml sampleN.yaml

Mount an ISO:

    vctools.py mount vcenter --name server --path /path/to/file.iso --datastore datastore

Query Datastore Info:

    vctools.py query vcenter --cluster cluster --datastores

Reconfig Parameters

    help: vctools reconfig [-h|--help]

    # reconfigure config settings
    # lookup vmware sdk configspec for all options
    vctools.py reconfig <vc> <name> --cfgs memoryMB=<int>,numCPUs=<int>

    # reconfigure a disk
    vctools.py reconfig <vc> <name> --device disk --disk-id <int> --sizeGB <int>

    # reconfigure a network card
    vctools.py reconfig <vc> <name> --device nic --nic-id <int> --network <network>

Unmount an ISO:

    vctools.py umount vcenter --name server

Upload ISO to Datastore:

    vctools.py upload vcenter --iso /local/path/to/file.iso \
      --dest /remote/path/to/iso/folder --datastore datastore \
      --datacenter datacenter

Contributing:

Pull requests are welcome. Please follow PEP 8, and pylint is
recommended for ensuring the code follows those standards. Disabling
certain pylints is allowed (like star-args), so use your best
judgment. Please disable using a comment in the vicinity of where the
error occurs in the file. Keep maximum characters to 100 per line.

Here's a quick way to set it up in the Python intepreter and then you
can move freely around the interface. The commands dir() and getattr()
are very helpful.

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

    clusters = self.query.create_container(
        auth.session, auth.session.content.rootFolder, [vim.ComputeResource], True
    )

    vm_name = query.get_obj(virtual_machines.view, 'vm_name')

    dir(vm_name)

Thanks:

A special thanks goes out to VMware Onyx, as well as my colleagues,
which allowed me to make this code possible.
