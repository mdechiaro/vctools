#!/usr/bin/env python
# vim: ts=4 sw=4 et
"""Class for handling argparse parsers. Methods are configured as subparsers."""
import argparse
import os
import subprocess
import sys
import textwrap
from vctools import Logger
# pylint: disable=empty-docstring,missing-docstring

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
            description='vcenter tools cli'
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

        # general (parent)
        general_parser = argparse.ArgumentParser(add_help=False)

        general_parser.add_argument(
            'vcenter',
            help='vcenter fqdn'
        )

        genopts = general_parser.add_argument_group('general options')

        genopts.add_argument(
            '--passwd-file', metavar='',
            help='gpg encrypted passwd file'
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
            help='vcenter datacenter'
        )

        if defaults:
            general_parser.set_defaults(**defaults)

        return general_parser

    @classmethod
    def logging(cls, **defaults):

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

        usage = """
        ## add
        help: vctools add -h

        ### add a network card
        vctools add <vcenter> <name> --device nic --network <network>
        """
        add_parser = self.subparsers.add_parser(
            'add',
            parents=list(parents),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            usage=textwrap.dedent(usage),
            help='hardware to virtual machines.'
        )

        add_parser.set_defaults(cmd='add')

        add_type_opts = add_parser.add_argument_group('type options')

        add_parser.add_argument(
            'name',
            help='name attribute of virtual machine object, i.e. hostname'
        )

        add_type_opts.add_argument(
            '--device', metavar='', choices=['nic'],
            help='add hardware devices on virtual machines. choices=[%(choices)s]',
        )

        add_nic_opts = add_parser.add_argument_group('nic options')

        add_nic_opts.add_argument(
            '--network', metavar='',
            help='the network of the interface, i.e. vlan_1234_network'
        )

        add_nic_opts.add_argument(
            '--driver', metavar='', choices=['vmxnet3', 'e1000'],
            help='the network driver, default: vmxnet3'
        )

        if defaults:
            add_parser.set_defaults(**defaults)

    def create(self, *parents, **defaults):

        usage = """
        ## create
        help: vctools create -h

        ### create vm
        vctools create <vcenter> <config> <configN>

        ### clone vm from template
        vctools create <vcenter> <config> <configN> --template <template>
        """
        create_parser = self.subparsers.add_parser(
            'create',
            parents=list(parents),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            usage=textwrap.dedent(usage),
            help='create virtual machines'
        )

        create_parser.set_defaults(cmd='create')

        create_parser.add_argument(
            'config', nargs='+', type=self._fix_file_paths,
            help='yaml config for creating new virtual machines.'
        )

        create_parser.add_argument(
            '--power', action='store_true', default=True,
            help='power on the vm after creation. default: %(default)s'
        )

        create_parser.add_argument(
            '--template', metavar='',
            help='template to create new virtual machines.'
        )

        if defaults:
            create_parser.set_defaults(**defaults)

    def mount(self, *parents, **defaults):

        usage = """
        ## mount
        help: vctools mount -h

        ### mount iso
        vctools mount <vcenter> --name <server> --path <file.iso> --datastore <datastore>
        """
        mount_parser = self.subparsers.add_parser(
            'mount', parents=list(parents),
            usage=textwrap.dedent(usage),
            help='iso onto cdrom'
        )

        mount_parser.set_defaults(cmd='mount')

        mount_parser.add_argument(
            '--datastore', metavar='',
            help='name of datastore where the iso is located.'
        )

        mount_parser.add_argument(
            '--path', metavar='',
            help='path inside datastore where the iso is located.'
        )

        mount_parser.add_argument(
            '--name', nargs='+', metavar='',
            help='name attribute of virtual machine object.'
        )

        if defaults:
            mount_parser.set_defaults(**defaults)

    def power(self, *parents, **defaults):
        usage = """
        ## power
        help: vctools power -h

        ### adjust power state
        vctools power <vcenter> <on|off|reset|reboot|shutdown> --name name nameN
        """
        power_parser = self.subparsers.add_parser(
            'power', parents=list(parents),
            usage=textwrap.dedent(usage),
        )

        power_parser.set_defaults(cmd='power')

        power_parser.add_argument(
            'power', choices=['on', 'off', 'reset', 'reboot', 'shutdown'],
            help='change power state of vm'

        )

        power_parser.add_argument(
            '--name', nargs='+', metavar='',
            help='name attribute of virtual machine object.'
        )

        if defaults:
            power_parser.set_defaults(**defaults)

    def query(self, *parents, **defaults):

        usage = """
        ## query
        help: vctools query -h

        ### query basic vm config
        vctools query <vcenter> --vmconfig <name> <nameN>

        ### query debug vm config. note: write to separate file recommended.
        vctools query <vcenter> --vmconfig <name> --level debug --logfile <name>.out
        """
        query_parser = self.subparsers.add_parser(
            'query', parents=list(parents),
            usage=textwrap.dedent(usage),
            help='information'
        )

        query_parser.set_defaults(cmd='query')

        query_opts = query_parser.add_argument_group('query options')

        query_opts.add_argument(
            '--anti-affinity-rules', action='store_true',
            help='returns information about antiaffinityrules.'
        )

        query_opts.add_argument(
            '--datastores', action='store_true',
            help='returns information about datastores.'
        )

        query_opts.add_argument(
            '--datastore', metavar='',
            help='vcenter datastore.'
        )

        query_opts.add_argument(
            '--vms', action='store_true',
            help='returns information about virtual machines.'
        )

        query_opts.add_argument(
            '--folders', action='store_true',
            help='returns information about folders.'
        )

        query_opts.add_argument(
            '--networks', action='store_true',
            help='returns information about networks.'
        )

        query_opts.add_argument(
            '--clusters', action='store_true',
            help='returns information about computeresources.'
        )

        query_opts.add_argument(
            '--cluster', metavar='',
            help='vcenter computeresource.'
        )

        query_opts.add_argument(
            '--vmconfig', nargs='+', metavar='',
            help='virtual machine config'
        )

        query_opts.add_argument(
            '--vm-by-datastore', action='store_true',
            help='list the vms associated with datastore.'
        )
        query_opts.add_argument(
            '--vm-guest-ids', action='store_true',
            help='show all vm guest ids.'
        )

        query_vmcfg_opts = query_parser.add_argument_group('vmconfig options')

        query_vmcfg_opts.add_argument(
            '--createcfg', metavar='',
            help='create a build config from --vmconfig spec.'
        )


        if defaults:
            query_parser.set_defaults(**defaults)

    def reconfig(self, *parents, **defaults):

        usage = """
        ## reconfig
        help: vctools reconfig -h

        ### reconfigure config settings
        see VMware SDK vim.vm.ConfigSpec for all possible options
        vctools reconfig <vcenter> <name> --cfgs memoryMB=<int>,numCPUs=<int>
        vctools reconfig <vcenter> <name> --extra-cfgs guestinfo.metadata=<base64>

        ### convert vm to be a template
        vctools reconfig <vcenter> <name> --markastemplate

        ### move vm to another folder
        vctools reconfig <vcenter> <name> --folder <str>

        ### reconfigure a disk
        vctools reconfig <vcenter> <name> --device disk --disk-id <int> --sizeGB <int>

        ### reconfigure a network card
        vctools reconfig <vcenter> <name> --device nic --nic-id <int> --network <network>

        ### upgrade vm hardware
        vctools reconfig <vcenter> <name> --upgrade --scheduled
        """
        reconfig_parser = self.subparsers.add_parser(
            'reconfig',
            parents=list(parents),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            usage=textwrap.dedent(usage),
            help='virtual machine attributes and hardware'
        )
        reconfig_parser.set_defaults(cmd='reconfig')

        reconfig_type_opts = reconfig_parser.add_argument_group('type options')

        reconfig_parser.add_argument(
            'name',
            help='name attribute of virtual machine object, i.e. hostname'
        )

        reconfig_type_opts.add_argument(
            '--device', metavar='', choices=['disk', 'nic'],
            help='reconfigure hardware devices on virtual machines. choices=[%(choices)s]',
        )

        reconfig_type_opts.add_argument(
            '--cfgs', metavar='', type=self._mkdict,
            help='comma separated list of key values that represent config '
                 'settings such as memory or cpu. format: key=val,keyN=valN',
        )

        reconfig_type_opts.add_argument(
            '--extra-cfgs', metavar='', type=self._mkdict,
            help='comma separated list of key values that represent config '
                 'settings such as metadata and userdata. format: key=val,keyN=valN',
        )

        reconfig_type_opts.add_argument(
            '--folder', metavar='', type=str,
            help='move the vm to another folder. it must exist. '
        )

        reconfig_template_opts = reconfig_parser.add_argument_group('template options')

        reconfig_template_opts.add_argument(
            '--markastemplate', action='store_true', default=False,
            help='convert vm to a template. note template cannot be powered on.',
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
            help='upgrade vm hardware version.',
        )

        reconfig_upgrade_opts = reconfig_parser.add_argument_group('upgrade options')

        reconfig_upgrade_opts.add_argument(
            '--version', metavar='', type=str,
            help='upgrade hardware to specific version.'
        )
        reconfig_upgrade_opts.add_argument(
            '--scheduled', action='store_true',
            help='schedule a hardware upgrade on reboot.'
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

        usage = """
        ## umount
        help: vctools umount -h

        ### umount iso
        vctools umount <vcenter> --name name nameN
        """

        umount_parser = self.subparsers.add_parser(
            'umount', parents=list(parents),
            usage=textwrap.dedent(usage),
            help='iso from cdrom'
        )

        umount_parser.set_defaults(cmd='umount')

        umount_parser.add_argument(
            '--name', nargs='+',
            help='name attribute of virtual machine object.'
        )
        if defaults:
            umount_parser.set_defaults(**defaults)

    def upload(self, *parents, **defaults):

        usage = """
        ## upload
        help: vctools upload -h

        ### upload iso to remote datastore
        vctools upload vcenter --iso /local/path/to/file.iso \
            --dest /remote/path/to/iso/folder --datastore datastore \
            --datacenter datacenter
        """
        upload_parser = self.subparsers.add_parser(
            'upload', parents=list(parents),
            usage=textwrap.dedent(usage),
            help='data to remote datastore'
        )
        upload_parser.set_defaults(cmd='upload')

        upload_parser.add_argument(
            '--iso', nargs='+', metavar='',
            help='iso file that needs to be uploaded to vcenter.'
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
            help='verify ssl certificate. default: %(default)s'
        )

        if defaults:
            upload_parser.set_defaults(**defaults)

    def drs(self, *parents):
        usage = """

        help: vctools drs -h

        vctools drs <vcenter> anti-affinity add <name> --vms <vm1 vm2...>
        vctools drs <vcenter> anti-affinity delete <name>

        """
        drs_parser = self.subparsers.add_parser(
            'drs', parents=list(parents),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            usage=textwrap.dedent(usage),
            help='cluster drs rules'
        )

        drs_parser.set_defaults(cmd='drs')

        drs_parser.add_argument(
            'drs_type', choices=['anti-affinity'],
            help='options: anti-affinity'
        )
        drs_parser.add_argument(
            'function', choices=['add', 'delete'],
            help='options: add|delete'
        )
        drs_parser.add_argument(
            'name', metavar='', type=str,
            help='name of the drs rule'
        )
        drs_parser.add_argument(
            '--vms', nargs='+', metavar='', type=str,
            help='vms to be added to the drs rule'
        )
        drs_parser.add_argument(
            '--cluster', metavar='',
            help='vcenter computeresource'
        )
        drs_parser.add_argument(
            '--prefix', metavar='', type=str,
            help='cluster drs rule name prefix'
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
