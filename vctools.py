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
from vctools.prompts import Prompts
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

    # pylint: disable=too-many-branches
    def cfg_checker(self, cfg):
        """
        Checks config for a valid configuration, and prompts user if
        information is missing

        Args:
            cfg    (obj): Yaml object
            write (bool): Boolean writes answers to yaml file.
            output (str): Absolute path of output yaml file
        """
        # name
        if 'config' in cfg:
            if 'name' in cfg['config']:
                name = cfg['config']['name']
            else:
                name = Prompts.name()
        else:
            name = Prompts.name()

        # datacenter
        if not self.opts.datacenter:
            datacenter = Prompts.datacenters(self.auth.session)
            print('\n%s selected.' % (datacenter))
        else:
            datacenter = self.opts.datacenter

        # cluster
        if 'vcenter' in cfg:
            if 'cluster' in cfg['vcenter']:
                cluster = cfg['vcenter']['cluster']
        else:
            cluster = Prompts.clusters(self.auth.session)
            print('\n%s selected.' % (cluster))

        # datastore
        if 'vcenter' in cfg:
            if 'datastore' in cfg['vcenter']:
                datastore = cfg['vcenter']['datastore']
        else:
            datastore = Prompts.datastores(self.auth.session, cluster)
            print('\n%s selected.' % (datastore))

        # nics
        if 'devices' in cfg:
            if 'nics' in cfg['devices']:
                nics = cfg['devices']['nics']
                print('nics: %s' % (nics))
            else:
                nics = Prompts.networks(self.auth.session, cluster)
                print('\n%s selected.' % (','.join(nics)))
        else:
            nics = Prompts.networks(self.auth.session, cluster)
            print('\n%s selected.' % (','.join(nics)))

        # folder
        if 'vcenter' in cfg:
            if 'folder' in cfg['vcenter']:
                folder = cfg['vcenter']['folder']
        else:
            folder = Prompts.folders(self.auth.session, datacenter)
            print('\n%s selected.' % (folder))

        return (name, cluster, datastore, nics, folder)



    # pylint: disable=too-many-branches,too-many-locals,too-many-statements
    def create_wrapper(self, *yaml_cfg, **defaults):
        """
        Wrapper method for creating multiple VMs. If certain information was
        not provided in the yaml config (like a datastore), then the client
        will be prompted to select one inside the cfg_checker method.

        Args:
            prompt   (bool): True will prompt the user to accept the cfg
                before creating the VM.
            yaml_cfg (file): A yaml file containing the necessary information
                for creating a new VM.
            defaults (dict): A dict of default values from ConfigParser dotrc.
        """

        for cfg in yaml_cfg:
            spec = yaml.load(cfg)

            print(defaults)
            spec.update(defaults)
            print(spec)
            # sanitize the config and prompt for more info if necessary
            results = self.cfg_checker(spec)
            spec['config'].update({'name':results[0]})
            cluster = results[1]
            datastore = results[2]
            nics = results[3]
            folder = results[4]

            spec['devices'].update({'nics':nics})

            cluster_obj = Query.get_obj(self.clusters.view, cluster)
            pool = cluster_obj.resourcePool
            # convert kilobytes to gigabytes
            kb_to_gb = 1024*1024

            devices = []

            for scsi, disk in enumerate(spec['devices']['disks']):
                # setup the first four disks on a separate scsi controller
                devices.append(self.vmcfg.scsi_config(scsi))
                devices.append(
                    self.vmcfg.disk_config(
                        cluster_obj.datastore, datastore, disk*kb_to_gb,
                    )
                )

            for nic in nics:
                devices.append(self.vmcfg.nic_config(cluster_obj.network, nic))

            devices.append(self.vmcfg.cdrom_config())

            print(yaml.dump(spec, default_flow_style=False))
            answer = raw_input('Do you accept this config? [y|n]:')
            while True:
                if answer == 'y':
                    break
                if answer == 'n':
                    print('VM creation canceled by the user.')
                    sys.exit(1)

            # break for testing
            sys.exit(1)

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
                name = spec['name']

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
                # add default settings from dotrc file
                if self.vmconfig:
                    print('vmconfig: %s' % (self.vmconfig))
                    self.create_wrapper(*self.opts.config, **self.vmconfig)
                else:
                    print('no vmconfig')
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
