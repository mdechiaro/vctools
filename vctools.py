#!/usr/bin/python
# vim: ts=4 sw=4 et
"""
vctools is a Python module using pyVmomi which aims to simplify command-line
operations inside VMWare vCenter.

https://github.com/mdechiaro/vctools/
"""
# pylint: disable=no-name-in-module
from __future__ import print_function
import os
import sys
import copy
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
            for host in self.opts.name:
                if not self.opts.path.endswith('.iso'):
                    if self.opts.path.endswith('/'):
                        self.opts.path = self.opts.path + host + '.iso'
                    else:
                        self.opts.path = self.opts.path +'/'+ host +'.iso'
                # path is relative in vsphere, so we strip off the first char.
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
                self.opts.verify_ssl = bool(self.dotrc['upload']['verify_ssl'])


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

    # pylint: disable=too-many-branches, too-many-statements
    def cfg_checker(self, cfg):
        """
        Checks config for a valid configuration, and prompts user if
        information is missing

        Args:
            cfg    (obj): Yaml object
        """
        # name
        if 'vmconfig' in cfg:

            # name
            if 'name' in cfg['vmconfig']:
                name = cfg['vmconfig']['name']
            else:
                name = Prompts.name()
            # guestid
            if 'guestId' in cfg['vmconfig']:
                guestid = cfg['vmconfig']['guestId']
            else:
                guestid = Prompts.guestids()
                print('\n%s selected.' % (guestid))
            # cluster
            if 'cluster' in cfg['vmconfig']:
                cluster = cfg['vmconfig']['cluster']
            else:
                cluster = Prompts.clusters(self.auth.session)
                print('\n%s selected.' % (cluster))
            # datastore
            if 'datastore' in cfg['vmconfig']:
                datastore = cfg['vmconfig']['datastore']
            else:
                datastore = Prompts.datastores(self.auth.session, cluster)
                print('\n%s selected.' % (datastore))
            # datacenter
            if not self.opts.datacenter:
                datacenter = Prompts.datacenters(self.auth.session)
                print('\n%s selected.' % (datacenter))
            else:
                datacenter = self.opts.datacenter
            # nics
            if 'nics' in cfg['vmconfig']:
                nics = cfg['vmconfig']['nics']
                print('nics: %s' % (nics))
            else:
                nics = Prompts.networks(self.auth.session, cluster)
                print('\n%s selected.' % (','.join(nics)))
            # folder
            if 'folder' in cfg['vmconfig']:
                folder = cfg['vmconfig']['folder']
            else:
                folder = Prompts.folders(self.auth.session, datacenter)
                print('\n%s selected.' % (folder))
        else:
            name = Prompts.name()
            guestid = Prompts.guestids()
            print('\n%s selected.' % (guestid))
            cluster = Prompts.clusters(self.auth.session)
            print('\n%s selected.' % (cluster))
            datastore = Prompts.datastores(self.auth.session, cluster)
            print('\n%s selected.' % (datastore))
            datacenter = Prompts.datacenters(self.auth.session)
            print('\n%s selected.' % (datacenter))
            nics = Prompts.networks(self.auth.session, cluster)
            print('\n%s selected.' % (','.join(nics)))
            folder = Prompts.folders(self.auth.session, datacenter)
            print('\n%s selected.' % (folder))

        output = {
            'name': name,
            'guestId': guestid,
            'cluster': cluster,
            'datastore': datastore,
            'nics': nics,
            'folder': folder
        }

        return output

    def dict_merge(self, first, second):
        """
        Method deep merges two dictionaries of unknown value types and
        depth.

        Args:
            first (dict): The first dictionary
            second (dict): The second dictionary

        Returns:
            new (dict): A new dictionary that is a merge of the first and
                second
        """

        # deep copy the first to maintain it's structure
        new = copy.deepcopy(first)

        for key, value in second.iteritems():
            if key in new and isinstance(new[key], dict):
                new[key] = self.dict_merge(new[key], value)
            else:
                new[key] = copy.deepcopy(value)

        return new


    # pylint: disable=too-many-branches,too-many-locals,too-many-statements
    def create_wrapper(self, *yaml_cfg):
        """
        Wrapper method for creating multiple VMs. If certain information was
        not provided in the yaml config (like a datastore), then the client
        will be prompted to select one inside the cfg_checker method.

        Args:
            yaml_cfg (file): A yaml file containing the necessary information
                for creating a new VM. This file will override the defaults set
                in the dotrc file.
        """

        for cfg in yaml_cfg:

            spec = self.dict_merge(self.dotrc, yaml.load(cfg))
            # sanitize the config and prompt for more info if necessary
            results = self.cfg_checker(spec)

            spec['vmconfig'].update(self.dict_merge(spec['vmconfig'], results))

            server_cfg = copy.deepcopy(spec)

            cluster = spec['vmconfig']['cluster']
            datastore = spec['vmconfig']['datastore']
            folder = spec['vmconfig']['folder']


            cluster_obj = Query.get_obj(self.clusters.view, cluster)

            # list of scsi devices, max is 4.  Layout is a tuple containing the
            # key and configured device
            scsis = []
            # list of cdrom and disk devices
            devices = []

            # add the cdrom device
            devices.append(self.vmcfg.cdrom_config())

            # configure scsi controller and add disks to them.
            # to keep things simple, the max disks we allow in this example is
            # 4 (max scsi).
            for scsi, disk in enumerate(spec['vmconfig']['disks']):
                # setup the first four disks on a separate scsi controller
                # disk size is in GB
                scsis.append(self.vmcfg.scsi_config(scsi))
                devices.append(scsis[scsi][1])
                disk_cfg_opts = {}

                disk_cfg_opts.update(
                    {
                        'container' : cluster_obj.datastore,
                        'datastore' : datastore,
                        'size' : int(disk) * (1024*1024),
                        'key' : scsis[scsi][0],
                        'unit' : 0,
                    }
                )
                devices.append(self.vmcfg.disk_config(**disk_cfg_opts))

            # configure each network and add to devices
            for nic in spec['vmconfig']['nics']:
                nic_cfg_opts = {}
                nic_cfg_opts.update({'container' : cluster_obj.network, 'network' : nic})
                devices.append(self.vmcfg.nic_config(**nic_cfg_opts))
                #devices.append(self.vmcfg.nic_config(cluster_obj.network, nic))

            spec['vmconfig'].update({'deviceChange':devices})

            folder = Query.folders_lookup(
                self.datacenters.view, self.opts.datacenter, folder
            )

            # delete items that are no longer needed

            # delete keys that vSphere does not understand, so we can pass it a
            # dictionary to build the VM.
            del spec['vmconfig']['disks']
            del spec['vmconfig']['nics']
            del spec['vmconfig']['folder']
            del spec['vmconfig']['datastore']
            del spec['vmconfig']['datacenter']
            del spec['vmconfig']['cluster']

            pool = cluster_obj.resourcePool

            print('Creating VM %s' % spec['vmconfig']['name'])
            self.vmcfg.create(folder, datastore, pool, **spec['vmconfig'])

            # if mkbootiso is in the spec, then create the iso
            if 'mkbootiso' in spec:

                if 'template' in spec['mkbootiso']:
                    tmpl = MkBootISO.load_template(spec['mkbootiso'], spec['mkbootiso']['template'])
                    spec['mkbootiso'].update(self.dict_merge(tmpl, spec['mkbootiso']))

                print('\ncreating boot ISO for %s' % (spec['vmconfig']['name']))
                mkbootiso = spec['mkbootiso']
                iso_name = spec['vmconfig']['name'] + '.iso'

                # where mkbootiso should write the iso file
                if 'destination' in spec['mkbootiso']:
                    iso_path = spec['mkbootiso']['destination']
                else:
                    iso_path = '/tmp'

                MkBootISO.updateiso(
                    mkbootiso['source'], mkbootiso['ks'], **mkbootiso['options']
                )
                MkBootISO.createiso(mkbootiso['source'], iso_path, iso_name)

            if 'vctools' in spec:
                # run additional argparse options if declared in yaml cfg.
                if 'upload' in spec['vctools']:
                    datastore = self.dotrc['upload']['datastore']
                    dest = self.dotrc['upload']['dest']
                    verify_ssl = bool(self.dotrc['upload']['verify_ssl'])

                    # trailing slash is in upload method, so we strip it out
                    if dest.endswith('/'):
                        dest = dest.rstrip('/')

                    # path is relative (strip first character)
                    if dest.startswith('/'):
                        dest = dest.lstrip('/')

                    # verify_ssl needs to be a boolean value.
                    if verify_ssl:
                        verify_ssl = bool(self.dotrc['upload']['verify_ssl'])

                    if iso_path:
                        iso = iso_path + '/' + iso_name
                    else:
                        iso = spec['upload']['iso']

                    self.upload_wrapper(datastore, dest, verify_ssl, iso)
                    print('\n')

                if 'mount' in spec['vctools']:
                    datastore = self.dotrc['mount']['datastore']
                    path = self.dotrc['mount']['path']
                    name = spec['vmconfig']['name']

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

                if 'power' in spec['vctools']:
                    state = spec['vctools']['power']
                    name = spec['vmconfig']['name']

                    self.power_wrapper(state, name)
                    print('\n')

            return server_cfg


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

            print('Mounting [%s] %s on %s' % (datastore, path, name))
            cdrom_cfg = []
            key, controller = Query.get_key(host, 'CD/DVD')

            cdrom_cfg_opts = {}
            cdrom_cfg_opts.update(
                {
                    'datastore' : datastore,
                    'iso_path' : path,
                    'iso_name' : name,
                    'key': key,
                    'controller' : controller,
                }
            )
            cdrom_cfg.append(self.vmcfg.cdrom_config(**cdrom_cfg_opts))

            config = {'deviceChange' : cdrom_cfg}
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
            print('%s changing power state to %s' % (name, state))
            self.vmcfg.power(host, state)


    def umount_wrapper(self, *names):
        """
        Wrapper method for un-mounting isos on multiple VMs.

        Args:
            names (tuple): a tuple of VM names in vCenter.
        """
        for name in names:
            host = self.query.get_obj(
                self.virtual_machines.view, name
            )

            key, controller = Query.get_key(host, 'CD/DVD')

            print('Unmounting ISO on %s' % (name))
            cdrom_cfg = []
            cdrom_cfg_opts = {}
            cdrom_cfg_opts.update(
                {
                    'umount' : True,
                    'key' : key,
                    'controller' : controller,
                }
            )
            cdrom_cfg.append(self.vmcfg.cdrom_config(**cdrom_cfg_opts))
            #cdrom_cfg.append(self.vmcfg.cdrom_config(umount=True, key=key,
            #    controller=controller))
            config = {'deviceChange' : cdrom_cfg}
            self.vmcfg.reconfig(host, **config)


    def upload_wrapper(self, datastore, dest, verify_ssl, *isos):
        """
        Wrapper method for uploading multiple isos into a datastore.

        Args:
            isos (tuple): a tuple of isos locally on machine that will be
                uploaded.  The path for each iso should be absolute.
        """
        for iso in isos:
            print('uploading ISO: %s' % (iso))
            print('file size: %s' % (self.query.disk_size_format(os.path.getsize(iso))))
            print('remote location: [%s] %s' % (datastore, dest))

            print('This may take some time.')
            upload_args = {}

            # pylint: disable=protected-access
            upload_args.update(
                {
                    'host': self.opts.vc,
                    'cookie' : self.auth.session._stub.cookie,
                    'datacenter' : self.opts.datacenter,
                    'dest_folder' : dest,
                    'datastore' : datastore,
                    'iso' : iso,
                    'verify' : verify_ssl,
                }
            )

            result = self.vmcfg.upload_iso(**upload_args)

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
                if self.opts.config:
                    cfgs = []
                    cfgs.append(self.create_wrapper(*self.opts.config))
                    for cfg in cfgs:
                        filename = cfg['vmconfig']['name'] + '.yaml'
                        print(
                            yaml.dump(cfg, default_flow_style=False),
                            file=open(filename, 'w')
                        )
                else:
                    # allow for prompts for vm creation if necessary
                    self.create_wrapper()


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
                    if self.opts.cluster:
                        datastores = self.query.return_datastores(
                            self.clusters.view, self.opts.cluster
                        )

                        for row in datastores:
                            print('{0:30}\t{1:10}\t{2:10}\t{3:6}\t{4:10}\t{5:6}'.format(*row))
                    else:
                        print('--cluster <name> required with --datastores flag')

                if self.opts.folders:
                    if self.opts.cluster:
                        folders = self.query.list_vm_folders(
                            self.datacenters.view, self.opts.datacenter
                        )
                        folders.sort()
                        for folder in folders:
                            print(folder)
                    else:
                        print('--datacenter <name> required with --folders flag')

                if self.opts.clusters:
                    clusters = self.query.list_obj_attrs(self.clusters, 'name')
                    clusters.sort()
                    for cluster in clusters:
                        print(cluster)

                if self.opts.networks:
                    if self.opts.cluster:
                        cluster = self.query.get_obj(
                            self.clusters.view, self.opts.cluster
                        )
                        networks = self.query.list_obj_attrs(
                            cluster.network, 'name', view=False
                        )
                        networks.sort()
                        for net in networks:
                            print(net)
                    else:
                        print('--cluster <name> required with --networks flag')


                if self.opts.vms:
                    vms = self.query.list_vm_info(self.datacenters.view, self.opts.datacenter)
                    for key, value in vms.iteritems():
                        print(key, value)

            self.auth.logout()

        except ValueError as err:
            print(err)

        except vim.fault.InvalidLogin as loginerr:
            print(loginerr.msg)
            sys.exit(2)

        except KeyboardInterrupt:
            print('Interrupt caught, logging out and exiting.')
            self.auth.logout()
            sys.exit(1)


if __name__ == '__main__':
    # pylint: disable=invalid-name
    vc = VCTools()
    sys.exit(vc.main())
