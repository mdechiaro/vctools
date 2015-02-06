vctools
======


vctools is a Python module using pyVmomi which aims to simplify command-line operations inside vCenter.  The current state of this project is beta, and so far it can do the following:
  - Build a new VM using a yaml config
  - Generate a HTML5 console url from the command-line
  - Query various information useful for building new VMs, such as datastores, networks, folders.
  - Upload local ISOs to remote datastores
  - Mount ISOs

Dependencies:
  - Python 2.6+
  - python-argparse
  - python-requests
  - python-yaml
  - pyVmomi 

Usage:

Create a New VM:

    ./vctools.py create vcenter sample.yaml

Console to VM:

    ./vctools.py console vcenter --name server

Mount an ISO:

    ./vctools.py mount vcenter --name server --path /path/to/file.iso --datastore datastore


Query Datastore Info:

    ./vctools.py query vcenter --cluster cluster --datastores

Upload ISO to Datastore:

    ./vctools.py upload vcenter --iso /local/path/to/file.iso --dest /remote/path/to/iso/folder \
        --datastore datastore --datacenter datacenter

