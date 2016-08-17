#!/usr/bin/python
# vim: ts=4 sw=4 et
""" Class for handling argparse parsers. """
import argparse
import os
import subprocess
import sys
import textwrap
import yaml
from vctools import Logger

# pylint: disable=too-many-instance-attributes
class ArgParser(Logger):
    """Placeholder."""
    def __init__(self):
        self.syspath = sys.path[0]
        self.gitrev = subprocess.check_output(
            [
                'git', '--git-dir', self.syspath + '/.git', 'rev-parse', '--short', 'HEAD'
            ]
        )
        self.__version__ = self.gitrev
        self.help = None
        self.opts = None
        self.dotrc = None

        self.parser = argparse.ArgumentParser(
            description='vCenter Tools CLI'
        )

        self.parser.add_argument(
            '--version', '-v', action='version',
            version=self.__version__,
            help='version number'
        )

        # subparser
        self.subparsers = self.parser.add_subparsers(metavar='')
        # override options with defaults in dotfiles
        rootdir = os.path.dirname(os.path.abspath(__file__ + '/../'))
        rc_files = [rootdir + '/vctoolsrc.yaml', '~/.vctoolsrc.yaml']
        for rc_file in rc_files:
            try:
                dotrc_yaml = open(os.path.expanduser(rc_file))
                self.dotrc = yaml.load(dotrc_yaml)
            except IOError:
                pass

        if not self.dotrc:
            raise ValueError('Cannot load dotrc file.')

    @staticmethod
    def _mkdict(args):
        """
        Internal method for converting an argparse string key=value into dict.
        It passes each value through a for loop to correctly set its type,
        otherwise it returns it as a string.

        Example:
            key1=val1,key2=val2,key3=val3
        """

        params = dict(x.split('=') for x in args.split(','))

        for key, value in params.iteritems():
            if params[key].isdigit():
                params[key] = int(value)
            else:
                if params[key] == 'True':
                    params[key] = True
                elif params[key] == 'False':
                    params[key] = False

        return params


    def general_parser(self):
        """General Parser."""
        # general (parent)
        general_parser = argparse.ArgumentParser(add_help=False)
        general_parser.add_argument(
            'vc',
            help='vCenter host'
        )
        general_parser.add_argument(
            '--passwd-file', metavar='',
            help='GPG encrypted passwd file'
        )
        general_parser.add_argument(
            '--user', metavar='',
            help='username'
        )
        general_parser.add_argument(
            '--domain', metavar='',
            help='domain'
        )
        general_parser.add_argument(
            '--passwd', metavar='',
            help='password'
        )

        # ConfigParser overrides
        if 'general' in self.dotrc:
            general_parser.set_defaults(**self.dotrc['general'])

        return general_parser

    def add_parser(self, parent):
        """ Add Hardware to Virtual Machines """
        # add
        usage = """

        help: vctools add -h

        vctools add <vc> <name> --device <options>
        
        # add a network card
        vctools add <vc> <name> --device nic  --network <network>
        """
        add_parser = self.subparsers.add_parser(
            'add',
            parents=[parent],
            formatter_class=argparse.RawDescriptionHelpFormatter,
            usage=textwrap.dedent(usage),
            description=textwrap.dedent(self.add_parser.__doc__),
            help='Add Hardware to Virtual Machines.'
        )
        add_parser.set_defaults(cmd='add')
        add_parser.add_argument(
            '--datacenter', metavar='', default='Linux',
            help='vCenter Datacenter. default: %(default)s'
        )

        add_type_opts = add_parser.add_argument_group('type options')

        add_parser.add_argument(
            'name',
            help='Name attribute of Virtual Machine object, i.e. hostname'
        )

        add_type_opts.add_argument(
            '--device', metavar='', choices=['nic'],
            help='Add hardware devices on Virtual Machines. choices=[%(choices)s]',
        )

        add_nic_opts = add_parser.add_argument_group('nic options')

        add_nic_opts.add_argument(
            '--network', metavar='',
            help='The network of the interface, i.e. vlan_1234_network'
        )
        add_nic_opts.add_argument(
            '--driver', metavar='', choices=['vmxnet3', 'e1000'],
            help='The network driver, default: vmxnet3'
        )

    def create_parser(self, parent):
        """Create Parser."""
        # create
        create_parser = self.subparsers.add_parser(
            'create', parents=[parent],
            description='Example: vctools create <vc> <config> <configN>',
            help='Create Virtual Machines'
        )
        create_parser.set_defaults(cmd='create')

        create_parser.add_argument(
            'config', nargs='+', type=file,
            help='YaML config for creating new Virtual Machines.'
        )

        create_parser.add_argument(
            '--datacenter', metavar='', default='Linux',
            help='vCenter Datacenter. default: %(default)s'
        )
        if 'create' in self.dotrc:
            create_parser.set_defaults(**self.dotrc['vmconfig']['datacenter'])


    def mount_parser(self, parent):
        """Mount Parser."""
        # mount
        mount_parser = self.subparsers.add_parser(
            'mount', parents=[parent],
            help='Mount ISO to CD-Rom device'
        )

        mount_parser.set_defaults(cmd='mount')

        mount_parser.add_argument(
            '--datastore', metavar='',
            help='Name of datastore where the ISO is located.'
        )

        mount_parser.add_argument(
            '--path', metavar='',
            help='Path inside datastore where the ISO is located.'
        )

        mount_parser.add_argument(
            '--name', nargs='+', metavar='',
            help='name attribute of Virtual Machine object.'
        )
        if 'mount' in self.dotrc:
            mount_parser.set_defaults(**self.dotrc['mount'])


    def power_parser(self, parent):
        """Power Parser."""
        # power
        power_parser = self.subparsers.add_parser(
            'power', parents=[parent],
            help='Power Management for Virtual Machines'
        )
        power_parser.set_defaults(cmd='power')

        power_parser.add_argument(
            'power', choices=['on', 'off', 'reset', 'reboot', 'shutdown'],
            help='change power state of VM'

        )
        power_parser.add_argument(
            '--name', nargs='+', metavar='',
            help='name attribute of Virtual Machine object.'
        )


    def query_parser(self, parent):
        """Query Parser."""
        # query
        query_parser = self.subparsers.add_parser(
            'query', parents=[parent],
            help='Query Info'
        )
        query_parser.set_defaults(cmd='query')

        query_parser.add_argument(
            '--datastores', action='store_true',
            help='Returns information about Datastores.'
        )

        query_parser.add_argument(
            '--vms', action='store_true',
            help='Returns information about Virtual Machines.'
        )

        query_parser.add_argument(
            '--folders', action='store_true',
            help='Returns information about Folders.'
        )

        query_parser.add_argument(
            '--networks', action='store_true',
            help='Returns information about Networks.'
        )

        query_parser.add_argument(
            '--clusters', action='store_true',
            help='Returns information about ComputeResources.'
        )

        query_parser.add_argument(
            '--cluster', metavar='',
            help='vCenter ComputeResource.'
        )

        query_parser.add_argument(
            '--datacenter', metavar='', default='Linux',
            help='vCenter Datacenter. default: %(default)s'
        )
        query_parser.add_argument(
            '--vmconfig', nargs='+', metavar='',
            help='Virtual machine config'
        )

    def reconfig_parser(self, parent):
        """ Reconfig VM Attributes and Hardware """
        # reconfig
        usage = """

        help: vctools reconfig -h

        vctools reconfig <vc> <name> [--cfgs|--device] <options>

        # reconfigure config settings
        # lookup vmware sdk configspec for all options
        vctools reconfig <vc> <name> --cfgs memoryMB=<int>,numCPUs=<int>

        # move vm to another folder
        vctools reconfig <vc> <name> --folder <str>

        # reconfigure a disk
        vctools reconfig <vc> <name> --device disk --disk-id <int> --sizeGB <int>

        # reconfigure a network card
        vctools reconfig <vc> <name> --device nic --nic-id <int> --network <network>
        """
        reconfig_parser = self.subparsers.add_parser(
            'reconfig',
            parents=[parent],
            formatter_class=argparse.RawDescriptionHelpFormatter,
            usage=textwrap.dedent(usage),
            description=textwrap.dedent(self.reconfig_parser.__doc__),
            help='Reconfigure Attributes for Virtual Machines.'
        )
        reconfig_parser.set_defaults(cmd='reconfig')
        reconfig_parser.add_argument(
            '--datacenter', metavar='', default='Linux',
            help='vCenter Datacenter. default: %(default)s'
        )

        reconfig_type_opts = reconfig_parser.add_argument_group('type options')

        reconfig_parser.add_argument(
            'name',
            help='Name attribute of Virtual Machine object, i.e. hostname'
        )

        reconfig_type_opts.add_argument(
            '--device', metavar='', choices=['disk', 'nic'],
            help='Reconfigure hardware devices on Virtual Machines. choices=[%(choices)s]',
        )

        reconfig_type_opts.add_argument(
            '--cfgs', metavar='', type=self._mkdict,
            help='A comma separated list of key values that represent config '
                 'settings such as memory or cpu. format: key=val,keyN=valN',
        )

        reconfig_type_opts.add_argument(
            '--folder', metavar='', type=str,
            help='Move the VM to another folder. It must exist. '
        )

        reconfig_disk_opts = reconfig_parser.add_argument_group('disk options')

        reconfig_disk_opts.add_argument(
            '--disk-id', metavar='', type=int,
            help='The number that represents the disk'
        )

        reconfig_disk_opts.add_argument(
            '--disk-prefix', metavar='', default='Hard disk',
            help='The disk label prefix: default: \"%(default)s\"'
        )
        reconfig_disk_opts.add_argument(
            '--sizeGB', type=int, metavar='',
            help='New size hard disk in GB'
        )

        reconfig_nic_opts = reconfig_parser.add_argument_group('nic options')

        reconfig_nic_opts.add_argument(
            '--nic-id', metavar='', type=int,
            help='The number that represents the network card.'
        )
        reconfig_nic_opts.add_argument(
            '--nic-prefix', metavar='', default='Network adapter',
            help='The network label prefix: default: \"%(default)s\"'
        )
        reconfig_nic_opts.add_argument(
            '--network', metavar='',
            help='The network of the interface, i.e. vlan_1234_network'
        )
        reconfig_nic_opts.add_argument(
            '--driver', metavar='', choices=['vmxnet3', 'e1000'],
            help='The network driver, default: vmxnet3'
        )

    def umount_parser(self, parent):
        """ Umount Parser """
        # umount
        umount_parser = self.subparsers.add_parser(
            'umount', parents=[parent],
            help='Unmount ISO from CD-Rom device'
        )

        umount_parser.set_defaults(cmd='umount')

        umount_parser.add_argument(
            '--name', nargs='+',
            help='name attribute of Virtual Machine object.'
        )


    def upload_parser(self, parent):
        """ Upload Parser """
        # upload
        upload_parser = self.subparsers.add_parser(
            'upload', parents=[parent],
            help='Upload File'
        )
        upload_parser.set_defaults(cmd='upload')

        upload_parser.add_argument(
            '--iso', nargs='+', metavar='',
            help='iso file that needs to be uploaded to vCenter.'
        )

        upload_parser.add_argument(
            '--dest', metavar='',
            help='destination folder where the iso will reside.'
        )

        upload_parser.add_argument(
            '--datastore', metavar='', default='ISO_Templates',
            help='datastore where the iso will reside.  default: %(default)s'
        )

        upload_parser.add_argument(
            '--verify-ssl', metavar='', default=False,
            help='verify SSL certificate. default: %(default)s'
        )

        upload_parser.add_argument(
            '--datacenter', metavar='', default='Linux',
            help='vCenter Datacenter. default: %(default)s'
        )
        if 'upload' in self.dotrc:
            upload_parser.set_defaults(**self.dotrc['upload'])


    def setup_args(self):
        """Method loads all the argparse parsers."""

        general_parser = self.general_parser()
        self.add_parser(general_parser)
        self.create_parser(general_parser)
        self.mount_parser(general_parser)
        self.power_parser(general_parser)
        self.query_parser(general_parser)
        self.reconfig_parser(general_parser)
        self.umount_parser(general_parser)
        self.upload_parser(general_parser)
