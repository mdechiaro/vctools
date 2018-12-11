"""Various config options for Virtual Machines."""
#!/usr/bin/env python
# vim: ts=4 sw=4 et


import os
import socket
import copy
import requests
from pyVmomi import vim # pylint: disable=E0611
from vctools.prompts import Prompts
from vctools.query import Query
from vctools.vmconfig import VMConfig
from vctools import Logger

class VMConfigHelper(VMConfig, Logger):
    """Various config options for Virtual Machines."""
    def __init__(self, auth, opts, dotrc):
        VMConfig.__init__(self)
        self.auth = auth
        self.opts = opts
        self.dotrc = dotrc
        self.datacenters = Query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.Datacenter], True
        )
        self.clusters = Query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.ComputeResource], True
        )
        self.folders = Query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.Folder], True
        )
        self.virtual_machines = Query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.VirtualMachine], True
        )
        self.dvs = Query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.dvs.DistributedVirtualPortgroup], True,
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

        for key, value in second.items():
            if key in new and isinstance(new[key], dict):
                new[key] = self.dict_merge(new[key], value)
            else:
                new[key] = copy.deepcopy(value)

        return new

    def create_wrapper(self, **spec):
        """
        Wrapper method for creating VMs. If certain information was
        not provided in the yaml config (like a datastore), then the client
        will be prompted to select one inside the cfg_checker method.

        Args:
            yaml_cfg (file): A yaml file containing the necessary information
                for creating a new VM. This file will override the defaults set
                in the dotrc file.
        """

        # create a copy before manipulating the data for vsphere
        server_cfg = copy.deepcopy(spec)

        cluster = spec['vmconfig']['cluster']
        datastore = spec['vmconfig']['datastore']
        folder = spec['vmconfig']['folder']

        del server_cfg['general']['passwd']

        self.logger.info('vmconfig %s', server_cfg)
        cluster_obj = Query.get_obj(self.clusters.view, cluster)

        # list of cdrom and disk devices
        devices = []

        # add the cdrom device
        devices.append(self.cdrom_config())

        scsis = []
        if isinstance(spec['vmconfig']['disks'], dict):
            for scsi, disks in spec['vmconfig']['disks'].items():
                scsis.append(self.scsi_config(scsi))
                devices.append(scsis[scsi][1])
                for disk in enumerate(disks):
                    disk_cfg_opts = {}
                    disk_cfg_opts.update(
                        {
                            'container' : cluster_obj.datastore,
                            'datastore' : datastore,
                            'size' : int(disk[1]) * (1024*1024),
                            'controller' : scsis[scsi][0],
                            'unit' : disk[0],
                        }
                    )
                    devices.append(self.disk_config(**disk_cfg_opts))
        else:
            # attach up to four disks, each on its own scsi adapter
            for scsi, disk in enumerate(spec['vmconfig']['disks']):
                scsis.append(self.scsi_config(scsi))
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
                devices.append(self.disk_config(**disk_cfg_opts))

        # configure each network and add to devices
        for nic in spec['vmconfig']['nics']:
            if spec['vmconfig'].get('switch_type', None) == 'distributed':
                nic_cfg_opts = {}
                nic_cfg_opts.update(
                    {'container' : self.dvs.view, 'network' : nic, 'switch_type' : 'distributed'}
                )
                devices.append(self.nic_config(**nic_cfg_opts))
            else:
                nic_cfg_opts = {}
                nic_cfg_opts.update({'container' : cluster_obj.network, 'network' : nic})
                devices.append(self.nic_config(**nic_cfg_opts))

        spec['vmconfig'].update({'deviceChange':devices})

        if self.opts.datacenter:
            folder = Query.folders_lookup(
                self.datacenters.view, self.opts.datacenter, folder
            )
        else:
            folder = Query.folders_lookup(
                self.datacenters.view, spec['vmconfig']['datacenter'], folder
            )

        # delete keys that vSphere does not understand, so we can pass it a
        # dictionary to build the VM.
        del spec['vmconfig']['disks']
        del spec['vmconfig']['nics']
        del spec['vmconfig']['folder']
        del spec['vmconfig']['datastore']
        del spec['vmconfig']['datacenter']
        del spec['vmconfig']['cluster']

        if spec['vmconfig'].get('switch_type', None):
            del spec['vmconfig']['switch_type']

        pool = cluster_obj.resourcePool

        self.logger.debug(folder, datastore, pool, devices, spec)
        self.create(folder, datastore, pool, **spec['vmconfig'])

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
            host = Query.get_obj(
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
            cdrom_cfg.append(self.cdrom_config(**cdrom_cfg_opts))

            config = {'deviceChange' : cdrom_cfg}
            self.logger.debug(cdrom_cfg_opts, config)
            self.reconfig(host, **config)


    def power_wrapper(self, state, *names):
        """
        Wrapper method for changing the power state on multiple VMs.

        Args:
            state (str): choices: on, off, reset, reboot, shutdown
            names (str): a tuple of VM names in vCenter.
        """
        for name in names:
            host = Query.get_obj(self.virtual_machines.view, name)
            print('%s changing power state to %s' % (name, state))
            self.logger.debug(host, state)
            self.power(host, state)


    def umount_wrapper(self, *names):
        """
        Wrapper method for un-mounting isos on multiple VMs.

        Args:
            names (tuple): a tuple of VM names in vCenter.
        """
        for name in names:
            print('Umount ISO from %s' % (name))
            host = Query.get_obj(self.virtual_machines.view, name)

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
            cdrom_cfg.append(self.cdrom_config(**cdrom_cfg_opts))
            #cdrom_cfg.append(self.cdrom_config(umount=True, key=key,
            #    controller=controller))
            config = {'deviceChange' : cdrom_cfg}
            self.logger.debug(host, config)
            self.reconfig(host, **config)


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
                    iso, Query.disk_size_format(os.path.getsize(iso)), datastore, dest
                )
            )
            self.logger.info(
                'Uploading ISO: %s, file size: %s, remote location: [%s] %s',
                iso, Query.disk_size_format(os.path.getsize(iso)), datastore, dest
            )
            upload_args = {}

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

            result = self.upload_iso(**upload_args)
            self.logger.debug(result, upload_args)

            if result == 200 or 201:
                self.logger.info('result: %s %s uploaded successfully', result, iso)
            else:
                self.logger.error('result: %s %s upload failed', result, iso)

    def pre_create_hooks(self, **spec):
        """
        Additional steps for provisioning a VM prior to its creation

        Returns:
            spec (dict): Updated vmconfig
        """
        # create a boot iso
        if spec.get('mkbootiso', None):
            # if the guestId matches a default os config, then merge it
            for key, dummy in spec['mkbootiso']['defaults'].items():
                if key == spec['vmconfig']['guestId']:
                    spec['mkbootiso'] = self.dict_merge(
                        spec['mkbootiso']['defaults'][key], spec['mkbootiso']
                    )

                    # cleanup dict for server config
                    del spec['mkbootiso']['defaults']

                if not spec['mkbootiso'].get('options', None):
                    spec['mkbootiso']['options'] = {}

                if 'ubuntu' in spec['vmconfig']['guestId']:
                    if not spec['mkbootiso']['options'].get('netcfg/get_hostname', None):
                        fqdn = Prompts.fqdn()
                        spec['mkbootiso']['options'].update({
                            'netcfg/get_hostname' : fqdn
                        })
                    if not spec['mkbootiso']['options'].get('netcfg/get_ipaddress', None):
                        ipaddr, netmask, gateway = Prompts.ip_info()
                        spec['mkbootiso']['options'].update({
                            'netcfg/get_ipaddress' : ipaddr,
                            'netcfg/get_netmask' : netmask,
                            'netcfg/get_gateway' : gateway
                        })

                elif 'rhel' in spec['vmconfig']['guestId']:
                    if not spec['mkbootiso']['options'].get('hostname', None):
                        fqdn = Prompts.fqdn()
                        spec['mkbootiso']['options'].update({
                            'hostname' : fqdn
                        })
                    if not spec['mkbootiso']['options'].get('ip', None):
                        ipaddr, netmask, gateway = Prompts.ip_info()
                        spec['mkbootiso']['options'].update({
                            'ip' : ipaddr, 'netmask' : netmask, 'gateway' : gateway
                        })

            spec['mkbootiso'].update({'filename' : spec['vmconfig']['name'] + '.iso'})
            self.logger.info('mkbootiso %s', spec['mkbootiso'])
            mkbootiso_url = 'https://{0}/api/mkbootiso'.format(socket.getfqdn())
            headers = {'Content-Type' : 'application/json'}
            requests.post(mkbootiso_url, json=spec['mkbootiso'], headers=headers, verify=False)

        return spec

    def post_create_hooks(self, **spec):
        """
        Additional steps for provisioning a VM after its creation

        Returns: None
        """

        # hooks for upload, mount, power
        if self.opts.upload:
            datastore = self.dotrc['upload']['datastore']
            dest = self.dotrc['upload']['dest']
            iso_path = '/tmp'
            verify_ssl = bool(self.dotrc['upload']['verify_ssl'])
            iso_name = spec['vmconfig']['name'] + '.iso'
            # trailing slash is in upload method, so we strip it out
            if dest.endswith('/'):
                dest = dest.rstrip('/')

            # path is relative (strip first character)
            if dest.startswith('/'):
                dest = dest.lstrip('/')

            if iso_path:
                iso = iso_path + '/' + iso_name
            else:
                iso = spec['upload']['iso']

            self.upload_wrapper(datastore, dest, verify_ssl, iso)

        if self.opts.mount:
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

        if self.opts.power:
            state = 'on'
            name = spec['vmconfig']['name']
            self.power_wrapper(state, name)

    def disk_recfg(self):
        """ Reconfigure a VM disk."""
        devices = []
        edit = True
        host = Query.get_obj(self.virtual_machines.view, self.opts.name)
        disk_cfg_opts = {}
        # KB
        tokbytes = 1024*1024
        label = self.opts.disk_prefix + ' ' + str(self.opts.disk_id)
        try:
            key, controller = Query.get_key(host, label)
        except IOError:
            pass
        if self.opts.disk_id:
            for item in host.config.hardware.device:
                if label == item.deviceInfo.label:
                    disk_new_size = self.opts.sizeGB * tokbytes
                    current_size = item.capacityInKB
                    current_size_gb = int(current_size / (1024*1024))
                    if disk_new_size == current_size:
                        raise ValueError(
                            'New size and existing size are equal'.format()
                        )
                    elif disk_new_size < current_size:
                        raise ValueError(
                            'Size {0} does not exceed {1}'.format(
                                disk_new_size, current_size
                            )
                        )
                    disk_delta = disk_new_size - current_size
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
                devices.append(self.disk_config(edit=edit, **disk_cfg_opts))
                self.logger.info(
                    '%s label: %s %s current_size: %s new_size: %s', host.name,
                    self.opts.disk_prefix, self.opts.disk_id, current_size_gb, self.opts.sizeGB
                )
                self.reconfig(host, **{'deviceChange': devices})

    def nic_recfg(self):
        """ Reconfigure a VM network adapter """
        devices = []
        edit = True
        host = Query.get_obj(self.virtual_machines.view, self.opts.name)
        nic_cfg_opts = {}
        label = self.opts.nic_prefix + ' ' + str(self.opts.nic_id)
        try:
            key, controller = Query.get_key(host, label)
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
                            self.nic_config(edit=edit, **nic_cfg_opts)
                        )
                        if devices:
                            self.logger.info(
                                '%s label: %s %s network: %s', host.name,
                                self.opts.nic_prefix, self.opts.nic_id,
                                self.opts.network
                            )
                            self.reconfig(host, **{'deviceChange': devices})

    def folder_recfg(self):
        """ Move a VM to another folder """
        host = Query.get_obj(self.virtual_machines.view, self.opts.name)
        folder = Query.folders_lookup(
            self.datacenters.view, self.opts.datacenter, self.opts.folder
        )
        self.logger.info('%s folder: %s', host.name, self.opts.folder)
        self.mvfolder(host, folder)

    def add_nic_recfg(self, vm_name):
        """ Add network adapter to VM. """
        # Prompt if network is not declared
        devices = []
        if not self.opts.network:
            # only first selection allowed for now
            network = Prompts.networks(vm_name.summary.runtime.host)[0]
        else:
            network = self.opts.network
        nic_cfg_opts = {}
        esx_host_net = vm_name.summary.runtime.host.network
        nic_cfg_opts.update({'container' : esx_host_net, 'network' : network})
        if self.opts.driver == 'e1000':
            nic_cfg_opts.update({'driver': 'VirtualE1000'})
        devices.append(self.nic_config(**nic_cfg_opts))
        if devices:
            self.logger.info(
                'add hardware %s network: %s', vm_name.name, network
            )
            self.reconfig(vm_name, **{'deviceChange': devices})
