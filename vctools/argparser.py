#!/usr/bin/env python
# vim: ts=4 sw=4 et
"""Class for handling argparse parsers. Methods are configured as subparsers."""
import argparse
import os
import subprocess
import sys
import textwrap
from vctools import Logger

class ArgParser(Logger):
    """Argparser class. It handles the user inputs and config files."""
    def __init__(self):
        self.syspath = sys.path[0]
        self.__version__ = subprocess.check_output(
            [
                'git', '--git-dir', self.syspath + '/.git', 'rev-parse', '--short', 'HEAD'
            ]
        ).decode('utf-8')

        self.parser = argparse.ArgumentParser(
            description='vCenter Tools CLI'
        )
        self.parser.add_argument(
            '--version', '-v', action='version',
            version=self.__version__,
            help='version number'
        )
        self.subparsers = self.parser.add_subparsers(metavar='')

        self.help = None
        self.opts = None
        self.dotrc = None

    def __call__(self, **dotrc):
        """
        Load the argparse parsers with the option for a dotrc override.

        Args:
            dotrc (dict): A dict were key is the argparse subparser and its
                val are the argument overrides.
        """
        self.dotrc = dotrc

        # parent_parsers are accessible to all subparsers
        parent_parsers = ['general', 'logging']
        parents = []

        # subparsers are methods that create positional arguments
        subparsers = [
            'add', 'create', 'drs', 'mount', 'power', 'query', 'reconfig', 'umount', 'upload'
        ]

        # load parsers and subparsers and override with dotrc dict
        for parent in parent_parsers:
            if self.dotrc:
                if parent in list(self.dotrc.keys()):
                    parents.append(getattr(self, str(parent))(**self.dotrc[str(parent)]))
                else:
                    parents.append(getattr(self, str(parent))())
            else:
                parents.append(getattr(self, str(parent))())

        for parser in subparsers:
            if self.dotrc:
                if parser in list(self.dotrc.keys()):
                    getattr(self, str(parser))(*parents, **self.dotrc[str(parser)])
                else:
                    getattr(self, str(parser))(*parents)
            else:
                getattr(self, str(parser))(*parents)

    @staticmethod
    def _fix_file_paths(args):
        """
        Internal method for expanding relative paths to OLDPWD to work around
        cd subshell and pipenv.
        """
        if not args.startswith(('/', '~')):
            args = os.path.join(os.environ['OLDPWD'], args)

        return open(args, 'r')

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

        for key, value in params.items():
            if params[key].isdigit():
                params[key] = int(value)
            else:
                if params[key] == 'True':
                    params[key] = True
                elif params[key] == 'False':
                    params[key] = False

        return params

    @classmethod
    def general(cls, **defaults):
        """General Parser."""
        # general (parent)
        general_parser = argparse.ArgumentParser(add_help=False)

        # positional argument
        general_parser.add_argument(
            'host',
            help='vCenter host'
        )

        genopts = general_parser.add_argument_group('general options')

        genopts.add_argument(
            '--passwd-file', metavar='',
            help='GPG encrypted passwd file'
        )

        genopts.add_argument(
            '--user', metavar='',
            help='username'
        )

        genopts.add_argument(
            '--domain', metavar='',
            help='domain'
        )

        genopts.add_argument(
            '--passwd', metavar='',
            help='password'
        )

        genopts.add_argument(
            '--rcfile', metavar='', type=argparse.FileType('r'),
            help='A custom config for vctools options'
        )

        genopts.add_argument(
            '--datacenter', metavar='',
            help='vCenter Datacenter'
        )

        if defaults:
            general_parser.set_defaults(**defaults)

        return general_parser

    @classmethod
    def logging(cls, **defaults):
        """ Logging Parser """
        # logging (parent)
        logging_parser = argparse.ArgumentParser(add_help=False)

        logging_opts = logging_parser.add_argument_group('logging options')

        logging_opts.add_argument(
            '--level', metavar='', choices=['info', 'debug'], default='info',
            help='set logging level choices=[%(choices)s] default: %(default)s'
        )

        logging_opts.add_argument(
            '--console-level', metavar='', choices=['info', 'error', 'debug'], default='error',
            help='set console log level choices=[%(choices)s] default: %(default)s'
        )
        logging_opts.add_argument(
            '--console-stream', metavar='', choices=['stdout', 'stderr'], default='stderr',
            help='set console logging stream output choices=[%(choices)s] default: %(default)s'
        )

        logging_opts.add_argument(
            '--logfile', metavar='', default='/var/log/vctools.log',
            help='set logging path: %(default)s'
        )

        if defaults:
            logging_parser.set_defaults(**defaults)

        return logging_parser

    def add(self, *parents, **defaults):
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
            parents=list(parents),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            usage=textwrap.dedent(usage),
            description=textwrap.dedent(self.add.__doc__),
            help='Add Hardware to Virtual Machines.'
        )

        add_parser.set_defaults(cmd='add')

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

        if defaults:
            add_parser.set_defaults(**defaults)

    def create(self, *parents, **defaults):
        """Create Parser."""
        # create
        create_parser = self.subparsers.add_parser(
            'create', parents=list(parents),
            description='Example: vctools create <vc> <config> <configN>',
            help='Create Virtual Machines'
        )

        create_parser.set_defaults(cmd='create')

        create_parser.add_argument(
            'config', nargs='+', type=self._fix_file_paths,
            help='YaML config for creating new Virtual Machines.'
        )

        create_parser.add_argument(
            '--power', action='store_true', default=True,
            help='Power on the VM after creation. default: %(default)s'
        )

        if defaults:
            create_parser.set_defaults(**defaults)

    def mount(self, *parents, **defaults):
        """Mount Parser."""
        # mount
        mount_parser = self.subparsers.add_parser(
            'mount', parents=list(parents),
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

        if defaults:
            mount_parser.set_defaults(**defaults)

    def power(self, *parents, **defaults):
        """Power Parser."""
        # power
        power_parser = self.subparsers.add_parser(
            'power', parents=list(parents),
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

        if defaults:
            power_parser.set_defaults(**defaults)

    def query(self, *parents, **defaults):
        """Query Parser."""
        # query
        query_parser = self.subparsers.add_parser(
            'query', parents=list(parents),
            help='Query Info'
        )

        query_parser.set_defaults(cmd='query')

        query_opts = query_parser.add_argument_group('query options')

        query_opts.add_argument(
            '--anti-affinity-rules', action='store_true',
            help='Returns information about AntiAffinityRules.'
        )

        query_opts.add_argument(
            '--datastores', action='store_true',
            help='Returns information about Datastores.'
        )

        query_opts.add_argument(
            '--datastore', metavar='',
            help='vCenter Datastore.'
        )

        query_opts.add_argument(
            '--vms', action='store_true',
            help='Returns information about Virtual Machines.'
        )

        query_opts.add_argument(
            '--folders', action='store_true',
            help='Returns information about Folders.'
        )

        query_opts.add_argument(
            '--networks', action='store_true',
            help='Returns information about Networks.'
        )

        query_opts.add_argument(
            '--clusters', action='store_true',
            help='Returns information about ComputeResources.'
        )

        query_opts.add_argument(
            '--cluster', metavar='',
            help='vCenter ComputeResource.'
        )

        query_opts.add_argument(
            '--vmconfig', nargs='+', metavar='',
            help='Virtual machine config'
        )

        query_opts.add_argument(
            '--vm-by-datastore', action='store_true',
            help='List the VMs associated with datastore.'
        )
        query_opts.add_argument(
            '--vm-guest-ids', action='store_true',
            help='Show all vm guest ids.'
        )

        query_vmcfg_opts = query_parser.add_argument_group('vmconfig options')

        query_vmcfg_opts.add_argument(
            '--createcfg', metavar='',
            help='Create a build config from --vmconfig spec.'
        )


        if defaults:
            query_parser.set_defaults(**defaults)

    def reconfig(self, *parents, **defaults):
        """ Reconfig VM Attributes and Hardware """
        # reconfig
        usage = """

        help: vctools reconfig -h

        vctools reconfig <vc> <name> [--cfgs|--device|--folder|--upgrade] <options>

        # reconfigure config settings
        # lookup vmware sdk configspec for all options
        vctools reconfig <vc> <name> --cfgs memoryMB=<int>,numCPUs=<int>

        # move vm to another folder
        vctools reconfig <vc> <name> --folder <str>

        # reconfigure a disk
        vctools reconfig <vc> <name> --device disk --disk-id <int> --sizeGB <int>

        # reconfigure a network card
        vctools reconfig <vc> <name> --device nic --nic-id <int> --network <network>

        # upgrade vm hardware
        vctools reconfig <vc> <name> --upgrade --scheduled
        """
        reconfig_parser = self.subparsers.add_parser(
            'reconfig',
            parents=list(parents),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            usage=textwrap.dedent(usage),
            description=textwrap.dedent(self.reconfig.__doc__),
            help='Reconfigure Attributes for Virtual Machines.'
        )
        reconfig_parser.set_defaults(cmd='reconfig')

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
            '--driver', metavar='', default='vmxnet3',
            choices=['vmxnet3', 'e1000'],
            help='The network driver, default: \"%(default)s\"'
        )
        reconfig_type_opts.add_argument(
            '--upgrade', action='store_true',
            help='Upgrade VM hardware version.',
        )

        reconfig_upgrade_opts = reconfig_parser.add_argument_group('upgrade options')

        reconfig_upgrade_opts.add_argument(
            '--version', metavar='', type=str,
            help='Upgrade hardware to specific version.'
        )
        reconfig_upgrade_opts.add_argument(
            '--scheduled', action='store_true',
            help='Schedule a hardware upgrade on reboot.'
        )
        reconfig_upgrade_opts.add_argument(
            '--policy', metavar='', default='always',
            choices=['always', 'never', 'on_soft_poweroff'],
            help='The upgrade policy to use with scheduling. ' +
            'choices: \"%(choices)s\" ' + 'default: \"%(default)s\" '
        )

        if defaults:
            reconfig_parser.set_defaults(**defaults)

    def umount(self, *parents, **defaults):
        """ Umount Parser """
        # umount
        umount_parser = self.subparsers.add_parser(
            'umount', parents=list(parents),
            help='Unmount ISO from CD-Rom device'
        )

        umount_parser.set_defaults(cmd='umount')

        umount_parser.add_argument(
            '--name', nargs='+',
            help='name attribute of Virtual Machine object.'
        )
        if defaults:
            umount_parser.set_defaults(**defaults)

    def upload(self, *parents, **defaults):
        """ Upload Parser """
        # upload
        upload_parser = self.subparsers.add_parser(
            'upload', parents=list(parents),
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

        if defaults:
            upload_parser.set_defaults(**defaults)

    def drs(self, *parents):
        """Distributed Resource Scheduler rules, currently only anti-affinity"""

        usage = """
        Cluster DRS Rules
        currently only anti-affinity rules are supported

        help: vctools drs -h

        vctools drs <vc> anti-affinity add <name> --vms <vm1 vm2...>
        vctools drs <vc> anti-affinity delete <name>

        """

        drs_parser = self.subparsers.add_parser(
            'drs', parents=list(parents),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            usage=textwrap.dedent(usage),
            description=textwrap.dedent(self.drs.__doc__),
            help='Cluster DRS rules'
        )

        drs_parser.set_defaults(cmd='drs')

        drs_parser.add_argument(
            'drs_type', choices=['anti-affinity'],
            help='options: anti-affinity (other options may come later)'
        )
        drs_parser.add_argument(
            'function', choices=['add', 'delete'],
            help='options: add|delete'
        )
        drs_parser.add_argument(
            'name', metavar='', type=str,
            help='Name of the DRS Rule'
        )
        drs_parser.add_argument(
            '--vms', nargs='+', metavar='', type=str,
            help='VMs to be added to the DRS rule'
        )
        drs_parser.add_argument(
            '--cluster', metavar='',
            help='vCenter ComputeResource'
        )
        drs_parser.add_argument(
            '--prefix', metavar='', type=str,
            help='Cluster DRS rule name prefix'
        )

    def sanitize(self, opts):
        """
        Sanitize arguments. This will override the user / config input to a supported state.

        Examples:
            - rename files
            - force booleans
            - absolute path checks

        Args:
           opts (obj): argparse namespace parsed args
        """
        # DRS rule names should always begin with the prefix
        if opts.cmd == 'drs':
            if not opts.prefix:
                opts.prefix = self.dotrc['clusterconfig']['prefix']
            if not opts.name.startswith(opts.prefix):
                opts.name = opts.prefix + opts.name

        # mount path needs to point to an iso, and it doesn't make sense to add
        # to the dotrc file, so this will append the self.opts.name value to it
        if opts.cmd == 'mount':
            for host in opts.name:
                if not opts.path.endswith('.iso'):
                    if opts.path.endswith('/'):
                        opts.path = opts.path + host + '.iso'
                    else:
                        opts.path = opts.path +'/'+ host +'.iso'
                # path is relative in vsphere, so we strip off the first char.
                if opts.path.startswith('/'):
                    opts.path = opts.path.lstrip('/')

        if opts.cmd == 'upload':
            # trailing slash is in upload method, so we strip it out here.
            if opts.dest.endswith('/'):
                opts.dest = opts.dest.rstrip('/')
            # path is relative in vsphere, so we strip off the first character.
            if opts.dest.startswith('/'):
                opts.dest = opts.dest.lstrip('/')
            # verify_ssl needs to be a boolean value.
            if opts.verify_ssl:
                opts.verify_ssl = bool(self.dotrc['upload']['verify_ssl'])

        return opts
