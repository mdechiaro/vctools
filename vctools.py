#!/usr/bin/python
# vim: ts=4 sw=4 et
"""
vctools is a Python module using pyVmomi which aims to simplify command-line
operations inside VMWare vCenter.

https://github.com/mdechiaro/vctools/
"""
# pylint: disable=no-name-in-module
from __future__ import print_function
from __future__ import division
import logging
from getpass import getuser
import os
import sys
import copy
import socket
import yaml
#
import requests
from pyVmomi import vim
from vctools.argparser import ArgParser
from vctools.auth import Auth
from vctools.vmconfig import VMConfig
from vctools.query import Query
from vctools.prompts import Prompts
from vctools.cfgchecker import CfgCheck
# pylint: disable=import-self
from vctools import Logger

# pylint: disable=too-many-instance-attributes
class VCTools(Logger):
    """
    Main VCTools class.
    """

    def __init__(self, opts):
        self.opts = opts
        self.auth = None
        self.clusters = None
        self.datacenters = None
        self.folders = None
        self.query = None
        self.virtual_machines = None
        self.vmcfg = None

    def create_containers(self):
        """
        Sets up different containers, or views, inside vSphere.

        These containers can then be queried to obtain different information
        about an object.
            vim.Datacenter
            vim.ComputeResource
            vim.Folder
            vim.VirtualMachine
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

            spec = self.dict_merge(argparser.dotrc, yaml.load(cfg))
            # sanitize the config and prompt for more info if necessary
            results = CfgCheck.cfg_checker(spec, self.auth, self.clusters, self.opts.datacenter)

            spec['vmconfig'].update(self.dict_merge(spec['vmconfig'], results))

            server_cfg = {}
            server_cfg['vmconfig'] = {}
            server_cfg['vmconfig'].update(spec['vmconfig'])

            cluster = spec['vmconfig']['cluster']
            datastore = spec['vmconfig']['datastore']
            folder = spec['vmconfig']['folder']

            self.logger.info('vmconfig %s', server_cfg)
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
                        'controller' : scsis[scsi][0],
                        'unit' : 0,
                    }
                )
                devices.append(self.vmcfg.disk_config(**disk_cfg_opts))

            # configure each network and add to devices
            for nic in spec['vmconfig']['nics']:
                nic_cfg_opts = {}
                nic_cfg_opts.update({'container' : cluster_obj.network, 'network' : nic})
                devices.append(self.vmcfg.nic_config(**nic_cfg_opts))

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

            self.vmcfg.create(folder, datastore, pool, **spec['vmconfig'])

            # create a boot iso
            if spec.get('mkbootiso', None):
                # if the guestId matches a default os config, then merge it
                for key, dummy in spec['mkbootiso']['defaults'].iteritems():
                    if key == spec['vmconfig']['guestId']:
                        spec['mkbootiso'] = self.dict_merge(
                            spec['mkbootiso']['defaults'][key], spec['mkbootiso']
                        )

                        # cleanup dict for server config
                        del spec['mkbootiso']['defaults']

                if not spec['mkbootiso'].get('ip', None):
                    ipaddr, netmask, gateway = Prompts.ip_info()
                    spec['mkbootiso']['options'].update({
                        'ip' : ipaddr, 'netmask' : netmask, 'gateway' : gateway
                    })

                spec['mkbootiso'].update({'filename' : spec['vmconfig']['name'] + '.iso'})
                self.logger.info('mkbootiso %s', spec['mkbootiso'])
                mkbootiso_url = 'https://{0}/api/mkbootiso'.format(socket.getfqdn())
                headers = {'Content-Type' : 'application/json'}
                requests.post(mkbootiso_url, json=spec['mkbootiso'], headers=headers, verify=False)
                server_cfg.update({'mkbootiso':spec['mkbootiso']})

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
            host = self.query.get_obj(self.virtual_machines.view, name)
            print('%s changing power state to %s' % (name, state))
            self.vmcfg.power(host, state)


    def umount_wrapper(self, *names):
        """
        Wrapper method for un-mounting isos on multiple VMs.

        Args:
            names (tuple): a tuple of VM names in vCenter.
        """
        for name in names:
            print('Umount ISO from %s' % (name))
            host = self.query.get_obj(self.virtual_machines.view, name)

            key, controller = Query.get_key(host, 'CD/DVD')

            self.logger.info('ISO on %s', name)
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
            print(
                'Uploading ISO: %s, file size: %s, remote location: [%s] %s' % (
                    iso, self.query.disk_size_format(os.path.getsize(iso)), datastore, dest
                )
            )
            self.logger.info(
                'Uploading ISO: %s, file size: %s, remote location: [%s] %s',
                iso, self.query.disk_size_format(os.path.getsize(iso)), datastore, dest
            )
            upload_args = {}

            # pylint: disable=protected-access
            upload_args.update(
                {
                    'host': self.opts.host,
                    'cookie' : self.auth.session._stub.cookie,
                    'datacenter' : self.opts.datacenter,
                    'dest_folder' : dest,
                    'datastore' : datastore,
                    'iso' : iso,
                    'verify' : verify_ssl,
                }
            )

            result = self.vmcfg.upload_iso(**upload_args)

            if result == 200 or 201:
                self.logger.info('result: %s %s uploaded successfully', result, iso)
            else:
                self.logger.info('result: %s %s upload failed', result, iso)


    def main(self):
        """
        This is the main method, which parses all the argparse options and runs
        the necessary code blocks if True.
        """

        # pylint: disable=too-many-nested-blocks
        try:
            self.logger.debug(self.opts)

            self.auth = Auth(self.opts.host)
            self.auth.login(
                self.opts.user, self.opts.passwd, self.opts.domain, self.opts.passwd_file
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

                        # hooks for upload, mount, power
                        if self.opts.upload:
                            datastore = argparser.dotrc['upload']['datastore']
                            dest = argparser.dotrc['upload']['dest']
                            iso_path = '/tmp'
                            verify_ssl = bool(argparser.dotrc['upload']['verify_ssl'])
                            iso_name = cfg['vmconfig']['name'] + '.iso'
                            # trailing slash is in upload method, so we strip it out
                            if dest.endswith('/'):
                                dest = dest.rstrip('/')

                            # path is relative (strip first character)
                            if dest.startswith('/'):
                                dest = dest.lstrip('/')

                            if iso_path:
                                iso = iso_path + '/' + iso_name
                            else:
                                iso = cfg['upload']['iso']

                            self.upload_wrapper(datastore, dest, verify_ssl, iso)

                        if self.opts.mount:
                            datastore = argparser.dotrc['mount']['datastore']
                            path = argparser.dotrc['mount']['path']
                            name = cfg['vmconfig']['name']

                            if not path.endswith('.iso'):
                                if path.endswith('/'):
                                    path = path + name + '.iso'
                                else:
                                    path = path +'/'+ name +'.iso'

                            # path is relative (strip first character)
                            if path.startswith('/'):
                                path = path.lstrip('/')

                            self.mount_wrapper(datastore, path, name)

                        if self.opts.power:
                            state = 'on'
                            name = cfg['vmconfig']['name']
                            self.power_wrapper(state, name)

                else:
                    # allow for prompts for vm creation if necessary
                    self.create_wrapper()

                    # hooks for upload, mount, power
                    if self.opts.mount:
                        datastore = argparser.dotrc['mount']['datastore']
                        path = argparser.dotrc['mount']['path']
                        name = cfg['vmconfig']['name']

                        if not path.endswith('.iso'):
                            if path.endswith('/'):
                                path = path + name + '.iso'
                            else:
                                path = path +'/'+ name +'.iso'

                        # path is relative (strip first character)
                        if path.startswith('/'):
                            path = path.lstrip('/')

                        self.mount_wrapper(datastore, path, name)

                    if self.opts.upload:
                        datastore = argparser.dotrc['upload']['datastore']
                        dest = argparser.dotrc['upload']['dest']
                        iso_path = '/tmp'
                        verify_ssl = bool(argparser.dotrc['upload']['verify_ssl'])
                        iso_name = cfg['vmconfig']['name'] + '.iso'
                        # trailing slash is in upload method, so we strip it out
                        if dest.endswith('/'):
                            dest = dest.rstrip('/')

                        # path is relative (strip first character)
                        if dest.startswith('/'):
                            dest = dest.lstrip('/')

                        # verify_ssl needs to be a boolean value.
                        if verify_ssl:
                            verify_ssl = bool(argparser.dotrc['upload']['verify_ssl'])

                        if iso_path:
                            iso = iso_path + '/' + iso_name
                        else:
                            iso = cfg['upload']['iso']

                        self.upload_wrapper(datastore, dest, verify_ssl, iso)

                    if self.opts.power:
                        state = 'on'
                        name = cfg['vmconfig']['name']
                        self.power_wrapper(state, name)

            if self.opts.cmd == 'mount':
                self.mount_wrapper(self.opts.datastore, self.opts.path, *self.opts.name)

            if self.opts.cmd == 'power':
                self.power_wrapper(self.opts.power, *self.opts.name)

            if self.opts.cmd == 'umount':
                self.umount_wrapper(*self.opts.name)

            if self.opts.cmd == 'upload':
                self.upload_wrapper(
                    self.opts.datastore, self.opts.dest,
                    self.opts.verify_ssl, *self.opts.iso
                )

            if self.opts.cmd == 'add':
                devices = []
                hostname = self.query.get_obj(self.virtual_machines.view, self.opts.name)

                # nics
                if self.opts.device == 'nic':
                    # Prompt if network is not declared
                    if not self.opts.network:
                        # only first selection allowed for now
                        network = Prompts.networks(hostname.summary.runtime.host)[0]
                    else:
                        network = self.opts.network
                    nic_cfg_opts = {}
                    esx_host_net = hostname.summary.runtime.host.network
                    nic_cfg_opts.update({'container' : esx_host_net, 'network' : network})
                    if self.opts.driver == 'e1000':
                        nic_cfg_opts.update({'driver': 'VirtualE1000'})
                    devices.append(self.vmcfg.nic_config(**nic_cfg_opts))
                    if devices:
                        self.logger.info(
                            'add hardware %s network: %s', hostname.name, network
                        )
                        self.vmcfg.reconfig(hostname, **{'deviceChange': devices})


            if self.opts.cmd == 'reconfig':
                devices = []
                host = self.query.get_obj(self.virtual_machines.view, self.opts.name)

                edit = True

                if self.opts.cfgs:
                    self.logger.info(
                        'reconfig: %s cfgs: %s', host.name,
                        ' '.join('%s=%s' % (k, v) for k, v in self.opts.cfgs.iteritems())
                    )
                    self.vmcfg.reconfig(host, **self.opts.cfgs)

                if self.opts.folder:
                    folder = Query.folders_lookup(
                        self.datacenters.view, self.opts.datacenter, self.opts.folder
                    )
                    self.logger.info('%s folder: %s', host.name, self.opts.folder)
                    self.vmcfg.mvfolder(host, folder)

                # disks
                if self.opts.device == 'disk':
                    disk_cfg_opts = {}
                    # KB
                    tokbytes = 1024*1024
                    label = self.opts.disk_prefix + ' ' + str(self.opts.disk_id)
                    try:
                        key, controller = self.query.get_key(host, label)
                    except IOError:
                        pass
                    if self.opts.disk_id:
                        for item in host.config.hardware.device:
                            if label == item.deviceInfo.label:
                                disk_new_size = self.opts.sizeGB * tokbytes
                                if disk_new_size == item.capacityInKB:
                                    raise ValueError(
                                        'New size and existing size are equal'.format()
                                    )
                                elif disk_new_size < item.capacityInKB:
                                    raise ValueError(
                                        'Size {0} does not exceed {1}'.format(
                                            disk_new_size, item.capacityInKB
                                        )
                                    )
                                disk_delta = disk_new_size - item.capacityInKB
                                ds_capacity_kb = item.backing.datastore.summary.capacity / 1024
                                ds_free_kb = item.backing.datastore.summary.freeSpace / 1024
                                threshold_pct = 0.10
                                if (ds_free_kb - disk_delta) / ds_capacity_kb < threshold_pct:
                                    raise ValueError(
                                        '{0} {1} disk space low, aborting.'.format(
                                            host.resourcePool.parent.name,
                                            item.backing.datastore.name
                                        )
                                    )
                                else:
                                    disk_cfg_opts.update(
                                        {
                                            'size' : disk_new_size,
                                            'key' : key,
                                            'controller' : controller,
                                            'unit' : item.unitNumber,
                                            'filename' : item.backing.fileName
                                        }
                                    )

                        if disk_cfg_opts:
                            devices.append(self.vmcfg.disk_config(edit=edit, **disk_cfg_opts))
                            self.logger.info(
                                '%s label: %s %s size: %s', host.name,
                                self.opts.disk_prefix, self.opts.disk_id, self.opts.sizeGB
                            )
                            self.vmcfg.reconfig(host, **{'deviceChange': devices})

                # nics
                if self.opts.device == 'nic':
                    nic_cfg_opts = {}
                    label = self.opts.nic_prefix + ' ' + str(self.opts.nic_id)
                    try:
                        key, controller = self.query.get_key(host, label)
                    except IOError:
                        pass
                    if self.opts.nic_id:
                        for item in host.config.hardware.device:
                            if label == item.deviceInfo.label:
                                if self.opts.network:
                                    nic_cfg_opts.update(
                                        {
                                            'key' : key,
                                            'controller' : controller,
                                            'container' : host.runtime.host.network,
                                            'network' : self.opts.network,
                                            'mac_address': item.macAddress,
                                            'unit' : item.unitNumber,
                                        }
                                    )
                                    if self.opts.driver == 'e1000':
                                        nic_cfg_opts.update({'driver': 'VirtualE1000'})
                                    devices.append(
                                        self.vmcfg.nic_config(edit=edit, **nic_cfg_opts)
                                    )
                                    if devices:
                                        self.logger.info(
                                            '%s label: %s %s network: %s', host.name,
                                            self.opts.nic_prefix, self.opts.nic_id,
                                            self.opts.network
                                        )
                                        self.vmcfg.reconfig(host, **{'deviceChange': devices})



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
                    if self.opts.datacenter:
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
                        cluster = self.query.get_obj(self.clusters.view, self.opts.cluster)
                        networks = self.query.list_obj_attrs(cluster.network, 'name', view=False)
                        networks.sort()
                        for net in networks:
                            print(net)
                    else:
                        print('--cluster <name> required with --networks flag')

                if self.opts.vms:
                    vms = self.query.list_vm_info(self.datacenters.view, self.opts.datacenter)
                    for key, value in vms.iteritems():
                        print(key, value)

                if self.opts.vmconfig:
                    for name in self.opts.vmconfig:
                        if self.opts.createcfg:
                            print(
                                yaml.dump(
                                    self.query.vm_config(
                                        self.virtual_machines.view, name, self.opts.createcfg
                                    ),
                                    default_flow_style=False
                                )
                            )
                        else:
                            print(
                                yaml.dump(
                                    self.query.vm_config(self.virtual_machines.view, name),
                                    default_flow_style=False
                                )
                            )


            self.auth.logout()

        except ValueError as err:
            self.logger.error(err, exc_info=False)
            self.auth.logout()
            sys.exit(3)

        except vim.fault.InvalidLogin as loginerr:
            self.logger.error(loginerr.msg, exc_info=False)
            sys.exit(2)

        except KeyboardInterrupt as err:
            self.logger.error(err, exc_info=False)
            self.auth.logout()
            sys.exit(1)


if __name__ == '__main__':
    # pylint: disable=invalid-name

    # setup argument parsing
    argparser = ArgParser()
    argparser.setup_args(**argparser.dotrc)
    options = argparser.sanitize(argparser.parser.parse_args())

    # setup logging
    log_level = options.level.upper()
    log_file = options.logfile
    log_format = '%(asctime)s %(username)s %(levelname)s %(module)s %(funcName)s %(message)s'
    logging.basicConfig(
        filename=log_file, level=getattr(logging, log_level), format=log_format
    )

    # set up logging to console for error messages
    console = logging.StreamHandler()
    console.setLevel(logging.ERROR)
    logging.getLogger().addHandler(console)

    # force username on logs and apply to all handlers
    # pylint: disable=too-few-public-methods
    class AddFilter(logging.Filter):
        """ Add filter class for adding attributes to logs """
        def filter(self, record):
            record.username = getuser()
            return True

    for handler in logging.root.handlers:
        handler.addFilter(AddFilter())

    vc = VCTools(options)
    sys.exit(vc.main())
