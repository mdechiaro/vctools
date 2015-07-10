#!/usr/bin/python

"""
vctools is a Python module using pyVmomi which aims to simplify command-line
operations inside VMWare vCenter.

https://github.com/mdechiaro/vctools/
"""
# pylint: disable=no-name-in-module
from __future__ import print_function
import argparse
import os
import sys
import yaml
#
from ConfigParser import SafeConfigParser
from pyVmomi import vim
from vctools.auth import Auth
from vctools.vmconfig import VMConfig
from vctools.query import Query
from vctools.wwwyzzerdd import Wwwyzzerdd


class VCTools(object):
    """
    Main VCTools class.
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self):
        self.__version__ = '1.2'
        self.auth = None
        self.clusters = None
        self.datacenters = None
        self.devices = []
        self.folders = None
        self.help = None
        self.opts = None
        self.query = None
        self.virtual_machines = None

    @staticmethod
    def _mkdict(args):
        """
        Internal method for converting an argparse string key=value into dict.
        It passes each value through a for loop to correctly set its type,
        otherwise it returns it as a string.

        format: key1=val1,key2=val2,key3=val3
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


    # pylint: disable=too-many-statements
    def options(self):
        """argparse command line options."""

        parser = argparse.ArgumentParser(
            description='vCenter Tools CLI'
        )

        parser.add_argument(
            '--version', '-v', action='version',
            version=self.__version__,
            help='version number'
        )

        # vc (parent)
        vc_parser = argparse.ArgumentParser(add_help=False)
        vc_parser.add_argument(
            'vc',
            help='vCenter host'
        )
        vc_parser.add_argument(
            '--passwd-file', metavar='',
            help='GPG encrypted passwd file'
        )



        # subparser
        subparsers = parser.add_subparsers(metavar='')


        # create
        create_parser = subparsers.add_parser(
            'create', parents=[vc_parser],
            help='Create Virtual Machines'
        )
        create_parser.set_defaults(cmd='create')

        create_parser.add_argument(
           'config', type=file,
            help='YaML config for creating new Virtual Machines.'
        )

        create_parser.add_argument(
           '--datacenter', metavar='', default='Linux',
            help='vCenter Datacenter. default: %(default)s'
        )

        # mount
        mount_parser = subparsers.add_parser(
            'mount', parents=[vc_parser],
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
           '--name', metavar='',
            help='name attribute of Virtual Machine object.'
        )


        # power
        power_parser = subparsers.add_parser(
            'power', parents=[vc_parser],
            help='Power Management for Virtual Machines'
        )
        power_parser.set_defaults(cmd='power')

        power_parser.add_argument(
            'power', choices=['on', 'off', 'reset', 'reboot', 'shutdown'],
            help='change power state of VM'

        )
        power_parser.add_argument(
           '--name', metavar='',
            help='name attribute of Virtual Machine object.'
        )

        # query
        query_parser = subparsers.add_parser(
            'query', parents=[vc_parser],
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


        # reconfig
        reconfig_parser = subparsers.add_parser(
            'reconfig', parents=[vc_parser],
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



        # umount
        umount_parser = subparsers.add_parser(
            'umount', parents=[vc_parser],
            help='Unmount ISO from CD-Rom device'
        )

        umount_parser.set_defaults(cmd='umount')

        umount_parser.add_argument(
           '--name',
            help='name attribute of Virtual Machine object.'
        )

        # upload
        upload_parser = subparsers.add_parser(
            'upload', parents=[vc_parser],
            help='Upload File'
        )
        upload_parser.set_defaults(cmd='upload')

        upload_parser.add_argument(
           '--iso', metavar='',
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

        # umount
        wizard_parser = subparsers.add_parser(
            'wizard',
            help='interactive wizard'
        )

        wizard_parser.set_defaults(cmd='wizard')

        # override options with defaults in dotfiles
        dotrc_parser = SafeConfigParser()
        dotrc_name = '~/.vctoolsrc'
        dotrc_path = os.path.expanduser(dotrc_name)

        dotrc_parser.read(dotrc_path)

        # set defaults for argparse options using a dotfile config
        vc_parser.set_defaults(**dict(dotrc_parser.items('general')))
        upload_parser.set_defaults(**dict(dotrc_parser.items('upload')))
        mount_parser.set_defaults(**dict(dotrc_parser.items('mount')))

        self.opts = parser.parse_args()
        self.help = parser.print_help

        # mount path needs to point to an iso, and it doesn't make sense to add
        # to the dotrc file, so this will append the self.opts.name value to it
        if self.opts.cmd == 'mount':
            if not self.opts.path.endswith('.iso'):
                if self.opts.path.endswith('/'):
                    self.opts.path = self.opts.path + self.opts.name + '.iso'
                else:
                    self.opts.path = self.opts.path +'/'+ self.opts.name +'.iso'


    def create_containers(self):
        """
        Sets up different containers, or views, inside vSphere.

        These containers can then be queried to obtain different information
        about an object.
        """

        self.datacenters = self.query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.Datacenter], True
        )

        self.clusters = self.query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.ComputeResource], True
        )

        self.folders = self.query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.Folder], True
        )

        self.virtual_machines = self.query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.VirtualMachine], True
        )

    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    def main(self):
        """
        This is the main method, which parses all the argparse options and runs
        the necessary code blocks if True.
        """

        try:
            self.options()

            if self.opts.cmd == 'wizard':
                wizard = Wwwyzzerdd()
                wizard.cmdloop()
                sys.exit(0)

            self.auth = Auth(self.opts.vc)
            if self.opts.passwd_file:
                self.auth.login(self.opts.passwd_file)
            else:
                self.auth.login()

            self.query = Query()
            vmcfg = VMConfig()

            self.create_containers()


            if self.opts.cmd == 'create':
                spec = yaml.load(self.opts.config)
                datastore = spec['vcenter']['datastore']

                cluster = self.query.get_obj(
                    self.clusters.view, spec['vcenter']['cluster']
                )

                pool = cluster.resourcePool

                folder = self.query.folders_lookup(
                    self.datacenters.view, self.opts.datacenter,
                    spec['vcenter']['folder']
                )

                # convert kilobytes to gigabytes
                kb_to_gb = 1024*1024

                for scsi, disk in enumerate(spec['devices']['disks']):
                    # setup the first four disks on a separate scsi controller
                    self.devices.append(vmcfg.scsi_config(scsi))
                    self.devices.append(
                        vmcfg.disk_config(
                            cluster.datastore, datastore, disk*kb_to_gb,
                            unit=scsi
                        )
                    )

                for nic in spec['devices']['nics']:
                    self.devices.append(vmcfg.nic_config(cluster.network, nic))

                self.devices.append(vmcfg.cdrom_config())

                vmcfg.create(
                    folder, pool, datastore, *self.devices, **spec['config']
                )

                if spec['vctools_cmds']:
                    # order should be the following if all are called.
                    # 1. create the iso
                    # 2. upload the iso
                    # 3. mount the iso
                    # 4. power on
                    # 5. umount the iso (some point in the future)
                    if spec['vctools_cmds']['upload']:
                        # upload iso
                        iso = spec['vctools_cmds']['upload']['iso']
                        dest = spec['vctools_cmds']['upload']['dest']
                        datastore = spec['vctools_cmds']['upload']['datastore']
                        # pylint: disable=line-too-long
                        verify_ssl = spec['vctools_cmds']['upload']['verify_ssl']
                        datacenter = spec['vctools_cmds']['upload']['datacenter']

                        print('uploading ISO: %s' % (iso))
                        print('file size: %s' % (
                            self.query.disk_size_format(
                                os.path.getsize(iso)
                                )
                            )
                        )
                        print('remote location: [%s] %s' % (
                            datastore, dest
                            )
                        )

                        print('This may take some time.')

                        # pylint: disable=protected-access
                        result = vmcfg.upload_iso(
                            self.opts.vc, self.auth.session._stub.cookie,
                            datacenter, dest, datastore,
                            iso, verify_ssl
                        )

                        print('result: %s' % (result))

                        if result == 200 or 201:
                            print('%s uploaded successfully' % (iso))
                        else:
                            print('%s uploaded failed' % (iso))

                    if spec['vctools_cmds']['mount']:
                        # mount iso
                        name = spec['vcenter']['config']['name']
                        datastore = spec['vctools_cmds']['mount']['datastore']
                        path = spec['vctools_cmds']['mount']['path']
                        #
                        host = self.query.get_obj(
                            self.virtual_machines.view, name
                        )
                        #
                        print('Mounting [%s] %s on %s' % (
                            datastore, path, name
                            )
                        )
                        cdrom_cfg = []
                        cdrom_cfg.append(vmcfg.cdrom_config(
                            datastore, path
                            )
                        )
                        config = {'deviceChange' : cdrom_cfg}
                        # pylint: disable=star-args
                        vmcfg.reconfig(host, **config)

                    if spec['vctools_cmds']['power']:
                        # change power state
                        name = spec['vcenter']['config']['name']
                        host = self.query.get_obj(
                            self.virtual_machines.view, name
                        )
                        print('%s changing power state to %s' % (
                            name, self.opts.power
                            )
                        )
                        vmcfg.power(
                            host, spec['vctools_cmds']['power']
                        )

                    if spec['vctools_cmds']['umount']:
                        name = spec['vcenter']['config']['name']
                        host = self.query.get_obj(
                            self.virtual_machines.view, name
                        )
                        print('Unmounting ISO on %s' % (name))
                        cdrom_cfg = []
                        cdrom_cfg.append(vmcfg.cdrom_config(umount=True))
                        config = {'deviceChange' : cdrom_cfg}
                        # pylint: disable=star-args
                        vmcfg.reconfig(host, **config)


            if self.opts.cmd == 'mount':
                if self.opts.datastore and self.opts.path and self.opts.name:
                    host = self.query.get_obj(
                        self.virtual_machines.view, self.opts.name
                    )

                    print('Mounting [%s] %s on %s' % (
                        self.opts.datastore, self.opts.path, self.opts.name
                        )
                    )
                    cdrom_cfg = []
                    cdrom_cfg.append(vmcfg.cdrom_config(
                        self.opts.datastore, self.opts.path
                        )
                    )
                    config = {'deviceChange' : cdrom_cfg}
                    # pylint: disable=star-args
                    vmcfg.reconfig(host, **config)


            if self.opts.cmd == 'power':
                if self.opts.name:
                    host = self.query.get_obj(
                        self.virtual_machines.view, self.opts.name
                    )
                    print('%s changing power state to %s' % (
                        self.opts.name, self.opts.power
                        )
                    )
                    vmcfg.power(host, self.opts.power)


            if self.opts.cmd == 'query':
                if self.opts.datastores:
                    self.query.list_datastore_info(
                        self.clusters.view, self.opts.cluster
                    )

                if self.opts.folders:
                    folders = self.query.list_vm_folders(
                        self.datacenters.view, self.opts.datacenter
                    )
                    folders.sort()
                    for folder in folders:
                        print(folder)

                if self.opts.clusters:
                    clusters = self.query.list_obj_attrs(self.clusters, 'name')
                    clusters.sort()
                    for cluster in clusters:
                        print(cluster)


                if self.opts.networks:
                    cluster = self.query.get_obj(
                        self.clusters.view, self.opts.cluster
                    )
                    networks = self.query.list_obj_attrs(
                        cluster.network, 'name', view=False
                    )
                    networks.sort()
                    for net in networks:
                        print(net)

                if self.opts.vms:
                    vms = self.query.list_vm_info(
                            self.datacenters.view, self.opts.datacenter
                    )
                    for key, value in vms.iteritems():
                        print(key, value)

            if self.opts.cmd == 'reconfig':
                host = self.query.get_obj(
                    self.virtual_machines.view, self.opts.name
                )
                vmcfg.reconfig(host, **self.opts.params)

            if self.opts.cmd == 'umount':
                host = self.query.get_obj(
                    self.virtual_machines.view, self.opts.name
                )

                print('Unmounting ISO on %s' % (self.opts.name))
                cdrom_cfg = []
                cdrom_cfg.append(vmcfg.cdrom_config(umount=True))
                config = {'deviceChange' : cdrom_cfg}
                # pylint: disable=star-args
                vmcfg.reconfig(host, **config)

            if self.opts.cmd == 'upload':
                print('uploading ISO: %s' % (self.opts.iso))
                print('file size: %s' % (
                    self.query.disk_size_format(
                        os.path.getsize(self.opts.iso)
                        )
                    )
                )
                print('remote location: [%s] %s' % (
                    self.opts.datastore, self.opts.dest
                    )
                )

                print('This may take some time.')

                # pylint: disable=protected-access
                result = vmcfg.upload_iso(
                    self.opts.vc, self.auth.session._stub.cookie,
                    self.opts.datacenter, self.opts.dest, self.opts.datastore,
                    self.opts.iso, self.opts.verify_ssl
                )

                print('result: %s' % (result))

                if result == 200 or 201:
                    print('%s uploaded successfully' % (self.opts.iso))
                else:
                    print('%s uploaded failed' % (self.opts.iso))


            self.auth.logout()

        except KeyboardInterrupt:
            print('Interrupt caught, logging out and exiting.')
            self.auth.logout()
            sys.exit(1)


if __name__ == '__main__':
    # pylint: disable=invalid-name
    vc = VCTools()
    sys.exit(vc.main())
