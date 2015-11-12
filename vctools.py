#!/usr/bin/python
# vim: tabstop=4 shiftwidth=4 expandtab
"""
vctools is a Python module using pyVmomi which aims to simplify command-line
operations inside VMWare vCenter.

https://github.com/mdechiaro/vctools/
"""
# pylint: disable=no-name-in-module
from __future__ import print_function
import os
import sys
import yaml
#
from pyVmomi import vim
from vctools.argparser import ArgParser
from vctools.auth import Auth
from vctools.vmconfig import VMConfig
from vctools.query import Query
from vctools.wwwyzzerdd import Wwwyzzerdd
from vctools.plugins.mkbootiso import MkBootISO

# pylint: disable=too-many-instance-attributes
class VCTools(ArgParser):
    """
    Main VCTools class.
    """

    def __init__(self):
        ArgParser.__init__(self)
        self.auth = None
        self.clusters = None
        self.datacenters = None
        self.folders = None
        self.query = None
        self.virtual_machines = None
        self.vmcfg = None


    def options(self):
        """Argparse command line options."""

        self.setup_args()
        self.opts = self.parser.parse_args()
        self.help = self.parser.print_help

        # mount path needs to point to an iso, and it doesn't make sense to add
        # to the dotrc file, so this will append the self.opts.name value to it
        if self.opts.cmd == 'mount':
            if not self.opts.path.endswith('.iso'):
                if self.opts.path.endswith('/'):
                    self.opts.path = self.opts.path + self.opts.name + '.iso'
                else:
                    self.opts.path = self.opts.path +'/'+ self.opts.name +'.iso'
            # path is relative in vsphere, so we strip off the first character.
            if self.opts.path.startswith('/'):
                self.opts.path = self.opts.path.lstrip('/')

        if self.opts.cmd == 'upload':
            # trailing slash is in upload method, so we strip it out here.
            if self.opts.dest.endswith('/'):
                self.opts.dest = self.opts.dest.rstrip('/')
            # path is relative in vsphere, so we strip off the first character.
            if self.opts.dest.startswith('/'):
                self.opts.dest = self.opts.dest.lstrip('/')
            # verify_ssl needs to be a boolean value.
            if self.opts.verify_ssl:
                self.opts.verify_ssl = self.dotrc_parser.getboolean(
                    'upload', 'verify_ssl'
                )


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


    def prompt_networks(self, cluster):
        """
        Method will prompt user to select a networks. Since multiple networks
        can be added to a VM, it will prompt the user to exit or add more.
        The networks should be selected in the order of which they want the
        interfaces set on the VM. For example, the first network selected will
        be configured on eth0 on the VM.

        Args:
            cluster (str): Name of cluster

        Returns:
            selected_networks (list): A list of selected networks
        """
        cluster = self.query.get_obj(
            self.clusters.view, cluster
        )
        networks = self.query.list_obj_attrs(
            cluster.network, 'name', view=False
        )
        networks.sort()

        print('\n')
        print('%s Networks Found.\n' % (len(networks)))

        for num, opt in enumerate(networks, start=1):
            print('%s: %s' % (num, opt))

        selected_networks = []

        while True:
            if selected_networks:
                print('selected: ' + ','.join(selected_networks))

            val = raw_input(
                '\nPlease select number:\n(Q)uit (S)how Networks\n'
                ).strip()

            # need to test whether selection is an integer or not.
            try:
                if int(val) <= len(networks):
                    # need to substract 1 since we start enumeration at 1.
                    val = int(val) - 1
                    selected_networks.append(networks[val])
                    continue
                else:
                    print('Invalid number.')
                    continue
            except ValueError:
                if val == 'Q':
                    break
                elif val == 'S':
                    for num, opt in enumerate(networks, start=1):
                        print('%s: %s' % (num, opt))
                else:
                    print('Invalid option.')
                    continue

        return selected_networks


    def prompt_datastores(self, cluster):
        """
        Method will prompt user to select a datastore from a cluster

        Args:
            cluster (str): Name of cluster

        Returns:
            datastore (str): Name of selected datastore
        """
        datastores = self.query.return_datastores(
            self.clusters.view, cluster
        )

        print('\n')
        if (len(datastores) -1) == 0:
            print('No Datastores Found.')
            sys.exit(1)
        else:
            print('%s Datastores Found.\n' % (len(datastores) - 1))

        for num, opt in enumerate(datastores):
            # the first item is the header information, so we will
            # not allow it as an option.
            if num == 0:
                print('\t%s' % (
                    # pylint: disable=star-args
                    '{0:30}\t{1:10}\t{2:10}\t{3:6}\t{4:10}\t{5:6}'.\
                        format(*opt)
                    )
                )
            else:
                print('%s: %s' % (
                    num,
                    # pylint: disable=star-args
                    '{0:30}\t{1:10}\t{2:10}\t{3:6}\t{4:10}\t{5:6}'.\
                        format(*opt)
                    )
                )

        while True:
            val = int(raw_input('\nPlease select number: ').strip())
            if val > 0 and val <= (len(datastores) - 1):
                break
            else:
                print('Invalid number')
                continue

        datastore = datastores[val][0]

        return datastore


    # pylint: disable=too-many-branches,too-many-locals,too-many-statements
    def create_wrapper(self, *yaml_cfg):
        """
        Wrapper method for creating multiple VMs. If certain information was
        not provided in the yaml config (like a datastore), then the client
        will be prompted to select one.

        Args:
            yaml_cfg (file): A yaml file containing the necessary information
                for creating a new VM.
        """

        for cfg in yaml_cfg:
            spec = yaml.load(cfg)

            # allow overrides of the datacenter in config.
            if 'datacenter' in spec['vcenter']:
                self.opts.datacenter = spec['vcenter']['datacenter']

            # check for datastore value in cfg and prompt user if empty.
            if 'datastore' in spec['vcenter']:
                datastore = spec['vcenter']['datastore']
            else:
                datastore = self.prompt_datastores(spec['vcenter']['cluster'])
                print('\n%s selected.' % (datastore))

            # check for network value in cfg and prompt user if empty.
            if 'nics' in spec['devices']:
                nics = spec['devices']['nics']
            else:
                nics = self.prompt_networks(spec['vcenter']['cluster'])
                print('\n%s selected.' % (','.join(nics)))

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

            devices = []

            for scsi, disk in enumerate(spec['devices']['disks']):
                # setup the first four disks on a separate scsi controller
                devices.append(self.vmcfg.scsi_config(scsi))
                devices.append(
                    self.vmcfg.disk_config(
                        cluster.datastore, datastore, disk*kb_to_gb, unit=scsi
                    )
                )

            for nic in nics:
                devices.append(self.vmcfg.nic_config(cluster.network, nic))

            devices.append(self.vmcfg.cdrom_config())

            # pylint: disable=star-args
            self.vmcfg.create(
                folder, pool, datastore, *devices, **spec['config']
            )

            # if mkbootiso is in the spec, then create the iso
            if 'mkbootiso' in spec:
                print('\ncreating boot ISO for %s' % (spec['config']['name']))
                mkbootiso = spec['mkbootiso']
                iso_name = spec['config']['name'] + '.iso'

                # where mkbootiso should write the iso file
                if 'destination' in spec['mkbootiso']:
                    iso_path = spec['mkbootiso']['destination']
                else:
                    iso_path = '/tmp'

                # pylint: disable=star-args
                MkBootISO.updateiso(
                    mkbootiso['source'], mkbootiso['ks'], **mkbootiso['options']
                )
                MkBootISO.createiso(mkbootiso['source'], iso_path, iso_name)

            # run additional argparse options if declared in yaml cfg.
            if 'upload' in spec:
                datastore = self.dotrc_parser.get('upload', 'datastore')
                dest = self.dotrc_parser.get('upload', 'dest')
                verify_ssl = self.dotrc_parser.get('upload', 'verify_ssl')

                # trailing slash is in upload method, so we strip it out here.
                if dest.endswith('/'):
                    dest = dest.rstrip('/')

                # path is relative (strip first character)
                if dest.startswith('/'):
                    dest = dest.lstrip('/')

                # verify_ssl needs to be a boolean value.
                if verify_ssl:
                    verify_ssl = self.dotrc_parser.getboolean(
                        'upload', 'verify_ssl'
                    )

                if iso_path:
                    iso = iso_path + '/' + iso_name
                else:
                    iso = spec['upload']['iso']

                self.upload_wrapper(datastore, dest, verify_ssl, iso)
                print('\n')

            if 'mount' in spec:
                datastore = self.dotrc_parser.get('mount', 'datastore')
                path = self.dotrc_parser.get('mount', 'path')
                name = spec['config']['name']

                if not path.endswith('.iso'):
                    if path.endswith('/'):
                        path = path + name + '.iso'
                    else:
                        path = path +'/'+ name +'.iso'

                # path is relative (strip first character)
                if path.startswith('/'):
                    path = path.lstrip('/')

                self.mount_wrapper(datastore, path, name)
                print('\n')

            if 'power' in spec:
                state = spec['power']
                name = spec['config']['name']

                self.power_wrapper(state, name)
                print('\n')


    def mount_wrapper(self, datastore, path, *names):
        """
        Wrapper method for mounting isos on multiple VMs.

        Args:
            datastore (str): Name of datastore where the ISO is located.
            path (str): Path inside datastore where the ISO is located.
            names (str): A tuple of VM names in vCenter.
        """
        for name in names:
            host = self.query.get_obj(
                self.virtual_machines.view, name
            )

            print('Mounting [%s] %s on %s' % (
                datastore, path, name
                )
            )
            cdrom_cfg = []
            cdrom_cfg.append(self.vmcfg.cdrom_config(datastore, path))

            config = {'deviceChange' : cdrom_cfg}
            # pylint: disable=star-args
            self.vmcfg.reconfig(host, **config)


    def power_wrapper(self, state, *names):
        """
        Wrapper method for changing the power state on multiple VMs.

        Args:
            state (str): choices: on, off, reset, reboot, shutdown
            names (str): a tuple of VM names in vCenter.
        """
        for name in names:
            host = self.query.get_obj(
                self.virtual_machines.view, name
            )
            print('%s changing power state to %s' % (
                name, state
                )
            )
            self.vmcfg.power(host, state)


    def umount_wrapper(self, *names):
        """
        Wrapper method for un-mounting isos on multiple VMs.

        Args:
            names (str): a tuple of VM names in vCenter.
        """
        for name in names:
            host = self.query.get_obj(
                self.virtual_machines.view, name
            )

            print('Unmounting ISO on %s' % (name))
            cdrom_cfg = []
            cdrom_cfg.append(self.vmcfg.cdrom_config(umount=True))
            config = {'deviceChange' : cdrom_cfg}
            # pylint: disable=star-args
            self.vmcfg.reconfig(host, **config)


    def upload_wrapper(self, datastore, dest, verify_ssl, *isos):
        """
        Wrapper method for uploading multiple isos into a datastore.

        Args:
            isos (str): a tuple of isos locally on machine that will be
                uploaded.  The path for each iso should be absolute.
        """
        for iso in isos:
            print('uploading ISO: %s' % (iso))
            print('file size: %s' % (
                self.query.disk_size_format(
                    os.path.getsize(iso)
                    )
                )
            )
            print('remote location: [%s] %s' % (datastore, dest))

            print('This may take some time.')

            # pylint: disable=protected-access
            result = self.vmcfg.upload_iso(
                self.opts.vc, self.auth.session._stub.cookie,
                self.opts.datacenter, dest, datastore,
                iso, verify_ssl
            )

            print('result: %s' % (result))

            if result == 200 or 201:
                print('%s uploaded successfully' % (iso))
            else:
                print('%s uploaded failed' % (iso))


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
            self.auth.login(
                self.opts.user, self.opts.domain, self.opts.passwd_file
            )

            self.query = Query()
            self.vmcfg = VMConfig()
            self.create_containers()

            if self.opts.cmd == 'create':
                self.create_wrapper(*self.opts.config)

            if self.opts.cmd == 'mount':
                self.mount_wrapper(
                    self.opts.datastore, self.opts.path, *self.opts.name
                )

            if self.opts.cmd == 'power':
                self.power_wrapper(self.opts.power, *self.opts.name)

            if self.opts.cmd == 'umount':
                self.umount_wrapper(*self.opts.name)

            if self.opts.cmd == 'upload':
                self.upload_wrapper(
                    self.opts.datastore, self.opts.dest,
                    self.opts.verify_ssl, *self.opts.iso
                )

            if self.opts.cmd == 'reconfig':
                host = self.query.get_obj(
                    self.virtual_machines.view, self.opts.name
                )
                self.vmcfg.reconfig(host, **self.opts.params)

            if self.opts.cmd == 'query':
                if self.opts.datastores:
                    datastores = self.query.return_datastores(
                        self.clusters.view, self.opts.cluster
                    )

                    for row in datastores:
                        # pylint: disable=star-args
                        print(
                            '{0:30}\t{1:10}\t{2:10}\t{3:6}\t{4:10}\t{5:6}'.\
                            format(*row)
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


            self.auth.logout()

        except KeyboardInterrupt:
            print('Interrupt caught, logging out and exiting.')
            self.auth.logout()
            sys.exit(1)


if __name__ == '__main__':
    # pylint: disable=invalid-name
    vc = VCTools()
    sys.exit(vc.main())
