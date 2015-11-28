#!/usr/bin/python
# vim: tabstop=4 shiftwidth=4 expandtab
""" Class for handling argparse parsers. """
import argparse
import os
import yaml
#

class ArgParser(object):
    """Placeholder."""
    def __init__(self):
        self.__version__ = '0.1.3'
        self.help = None
        self.opts = None

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
        dotrc_name = '~/.vctoolsrc.yaml'
        dotrc_yaml = open(os.path.expanduser(dotrc_name))
        self.dotrc = yaml.load(dotrc_yaml)


    @staticmethod
    def _mkdict(args):
        """
        Internal method for converting an argparse string key=value into dict.
        It passes each value through a for loop to correctly set its type,
        otherwise it returns it as a string.

        Example:
            key1=val1,key2=val2,key3=val3
        """

        args = args.replace(',', ' ').replace('=', ' ').split()
        params = dict(zip(args[0::2], args[1::2]))

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

        # ConfigParser overrides
        if 'general' in self.dotrc:
            general_parser.set_defaults(**self.dotrc['general'])

        return general_parser

    def create_parser(self, parent):
        """Create Parser."""
        # create
        create_parser = self.subparsers.add_parser(
            'create', parents=[parent],
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
            create_parser.set_defaults(**self.dotrc['create'])


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


    def reconfig_parser(self, parent):
        """ Reconfig Parser """
        # reconfig
        reconfig_parser = self.subparsers.add_parser(
            'reconfig', parents=[parent],
            help='Reconfigure Attributes for Virtual Machines.'
        )
        reconfig_parser.set_defaults(cmd='reconfig')

        reconfig_parser.add_argument(
           '--params', metavar='', type=self._mkdict,
            help='format: key1=val1,key2=val2,key3=val3'
        )

        reconfig_parser.add_argument(
           '--name', metavar='',
            help='name attribute of Virtual Machine object.'
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


    def wizard_parser(self):
        """ Wizard Parser """

        wizard_parser = self.subparsers.add_parser(
            'wizard',
            help='interactive wizard'
        )

        wizard_parser.set_defaults(cmd='wizard')


    def setup_args(self):
        """Method loads all the argparse parsers."""

        general_parser = self.general_parser()
        self.create_parser(general_parser)
        self.mount_parser(general_parser)
        self.power_parser(general_parser)
        self.query_parser(general_parser)
        self.reconfig_parser(general_parser)
        self.umount_parser(general_parser)
        self.upload_parser(general_parser)
        self.wizard_parser()
