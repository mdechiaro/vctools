#!/usr/bin/env python
# vim: ts=4 sw=4 et
"""Various config options for Virtual Machines."""

from random import uniform
import base64
import gzip
import io
import requests
from pyVmomi import vim # pylint: disable=E0611
from vctools.query import Query
from vctools.tasks import Tasks
from vctools import Logger

class VMConfig(Logger):
    """
    Class simplifies VM builds outside of using the client or Web App.
    Class can handle setting up a complete VM with multiple devices attached.
    It can also handle the addition of mutiple disks attached to multiple SCSI
    controllers, as well as multiple network interfaces.
    """

    def __init__(self):
        """ Define our class attributes here. """
        self.scsi_key = None

    def upload_iso(self, **kwargs):
        """
        Method uploads iso to dest_folder.

        Kwargs:
            host (str):        vCenter host
            cookie (attr):     Session Class Cookie (auth.session._stub.cookie)
            datacenter (str):  Name of Datacenter that has access to datastore.
            dest_folder (str): Folder that will store the iso.
            datastore (str):   Datastore that will store the iso.
            iso (str):         Absolute path of ISO file
            verify (bool):     Enable or disable SSL certificate validation.
        """
        host = kwargs.get('host', None)
        cookie = kwargs.get('cookie', None)
        datacenter = kwargs.get('datacenter', None)
        dest_folder = kwargs.get('dest_folder', None)
        datastore = kwargs.get('datastore', None)
        iso = kwargs.get('iso', None)
        verify = kwargs.get('verify', False)
        retry = kwargs.get('retry', True)

        # we need the absolute path to open the binary locally, but only the
        # filename for uploading to the datastore.
        if '/' in iso:
            # the last item in the list will be the filename
            iso_name = iso.split('/')[-1]
        else:
            iso_name = iso

        if not dest_folder.startswith('/'):
            dest_folder = '/' + dest_folder

        dest_folder = '/folder' + dest_folder

        cookie_val = cookie.split('"')[1]
        cookie = {'vmware_soap_session': cookie_val}

        params = {'dcPath' : datacenter, 'dsName' : datastore}
        url = 'https://' + host + dest_folder + '/' + iso_name

        try:
            with open(iso, 'rb') as data:
                response = requests.put(
                    url, params=params, cookies=cookie, data=data, verify=verify
                )
            self.logger.info('status: %s', response.status_code)
            self.logger.debug(response, kwargs)
            return response.status_code

        except requests.exceptions.ConnectionError as err:
            if retry:
                self.logger.error(err)
                self.logger.error('Upload failed, retrying')
                with open(iso, 'rb') as data:
                    response = requests.put(
                        url, params=params, cookies=cookie, data=data, verify=verify
                    )
                self.logger.debug(response, kwargs)
            else:
                self.logger.error(err, exc_info=False)
                self.logger.error('%s %s %s %s', url, params, cookie, verify)


    @classmethod
    def assign_ip(cls, **kwargs):
        """
        Method assigns a static IP on the vm

        Kwargs:
            dhcp (bool): Enable DHCP
            ipaddr (attr): IP Address
            netmask (str): Netmask
            gateway (str): Gateway
            domain (str): Domain
            dns (list): An array of DNS nameservers

        Returns:
            nic (obj): A configured object for IP assignments.  this should be
                appended to ConfigSpec devices attribute.
        """
        dhcp = kwargs.get('dhcp', None)
        ipaddr = kwargs.get('ipaddr', None)
        netmask = kwargs.get('netmask', None)
        gateway = kwargs.get('gateway', None)
        domain = kwargs.get('domain', None)
        dns = kwargs.get('dns', None)

        if dhcp:
            nic = vim.vm.customization.AdapterMapping()
            nic.adapter = vim.vm.customization.DhcpIpGenerator()
        else:
            nic.adapter = vim.vm.customization.IPSettings()
            nic.adapter.ip = vim.vm.customization.FixedIp()
            nic.adapter.ip.ipAddress = ipaddr
            nic.adapter.subnetMask = netmask
            nic.adapter.gateway = gateway
            nic.adapter.dnsDomain = domain
            nic.adapter.dnsServerList = dns

            return nic

        return nic

    @classmethod
    def scsi_config(cls, bus_number=0, shared_bus='noSharing'):
        """
        Method creates a SCSI Controller on the VM

        Args:
            bus_number (int): Bus number associated with this controller.
            shared_bus (str): Mode for sharing the SCSI bus.
                Valid Modes:
                    physicalSharing, virtualSharing, noSharing
        Returns:
            scsi (obj): A configured object for a SCSI Controller.  this should
                be appended to ConfigSpec devices attribute.
        """

        # randomize key for multiple scsi controllers
        key = int(uniform(-1, -100))

        scsi = vim.vm.device.VirtualDeviceSpec()
        scsi.operation = 'add'

        scsi.device = vim.vm.device.ParaVirtualSCSIController()
        scsi.device.key = key
        scsi.device.sharedBus = shared_bus
        scsi.device.busNumber = bus_number

        # grab defined key so devices can use it to connect to it.
        key = scsi.device.key

        return (key, scsi)


    @classmethod
    def cdrom_config(cls, **kwargs):
        """
        Method manages a CD-Rom Virtual Device.  If iso_path is not provided,
        then it will create the device.  Otherwise, it will attempt to mount
        the iso.  Iso must reside inside a datastore.  Use the upload_iso()
        method to use an iso stored locally.  If umount is True, then the
        method will attempt to umount the iso.

        When editing an existing device, the method will obtain the existing key
        so it can interact with the device.

        Args:
            datastore (str): Name of datastore
            iso_path (str):  Path to ISO
            iso_name (str):  Name of ISO on datastore
            umount (bool):   If True, then method will umount any existing ISO.
                If False, then method will create or mount the ISO.
            key (int): The key associated with the Cdrom device
            controller (int): The controller key associated with Cdrom device

        Returns:
            cdrom (obj): A configured object for a CD-Rom device.  this should
                be appended to ConfigSpec devices attribute.
        """
        datastore = kwargs.get('datastore', None)
        iso_path = kwargs.get('iso_path', None)
        iso_name = kwargs.get('iso_name', None)
        umount = kwargs.get('umount', None)
        key = kwargs.get('key', None)
        controller = kwargs.get('controller', None)

        cdrom = vim.vm.device.VirtualDeviceSpec()
        cdrom.device = vim.vm.device.VirtualCdrom()
        cdrom.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        cdrom.device.connectable.connected = True
        cdrom.device.connectable.startConnected = True
        cdrom.device.connectable.allowGuestControl = True

        # set default key value if it does not exist
        if not key:
            cdrom.device.key = 3002
        else:
            cdrom.device.key = key

        if not controller:
            cdrom.device.controllerKey = 201
        else:
            cdrom.device.controllerKey = controller

        # umount iso
        if umount:
            cdrom.operation = 'edit'
            cdrom.device.backing = vim.vm.device.VirtualCdrom.RemotePassthroughBackingInfo()
            cdrom.device.backing.exclusive = False

            return cdrom

        # mount iso
        if iso_path and iso_name and datastore and not umount:
            cdrom.operation = 'edit'

            if iso_path.endswith('.iso'):
                pass
            elif iso_path.endswith('/'):
                iso_path = iso_path + iso_name
            else:
                iso_path = iso_path + '/' + iso_name

            # path is relative, so we strip off the first character.
            if iso_path.startswith('/'):
                iso_path = iso_path.lstrip('/')

            cdrom.device.backing = vim.vm.device.VirtualCdrom.IsoBackingInfo()
            cdrom.device.backing.fileName = '['+ datastore + '] ' + iso_path

            return cdrom

        # create cdrom
        cdrom.operation = 'add'
        cdrom.device.backing = vim.vm.device.VirtualCdrom.RemotePassthroughBackingInfo()
        cdrom.device.backing.exclusive = False

        return cdrom


    @classmethod
    def disk_config(cls, edit=False, **kwargs):
        """
        Method returns configured VirtualDisk object

        Kwargs:
            container (obj): Cluster container object
            datastore (str): Name of datastore for the disk files location.
            size (int):      Integer of disk in kilobytes
            key  (int):      Integer value of scsi device
            unit (int):      unitNumber of device.
            mode (str):      The disk persistence mode.
            thin (bool):     If True, then it enables thin provisioning

        Returns:
            disk (obj): A configured object for a VMDK Disk.  this should
                be appended to ConfigSpec devices attribute.
        """
        # capacityInKB is deprecated but also a required field. See pyVmomi bug #218

        container = kwargs.get('container', None)
        datastore = kwargs.get('datastore', None)
        size = kwargs.get('size', None)
        key = kwargs.get('key', None)
        unit = kwargs.get('unit', 0)
        mode = kwargs.get('mode', 'persistent')
        thin = kwargs.get('thin', True)
        controller = kwargs.get('controller', None)
        filename = kwargs.get('filename', None)

        disk = vim.vm.device.VirtualDeviceSpec()

        if edit:
            disk.operation = 'edit'

            disk.device = vim.vm.device.VirtualDisk()
            disk.device.capacityInKB = size
            disk.device.key = key
            # controllerKey is tied to SCSI Controller
            disk.device.controllerKey = controller
            disk.device.unitNumber = unit
            disk.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
            disk.device.backing.fileName = filename
            disk.device.backing.diskMode = mode

        else:
            disk.operation = 'add'
            disk.fileOperation = 'create'

            disk.device = vim.vm.device.VirtualDisk()
            disk.device.capacityInKB = size
            # controllerKey is tied to SCSI Controller
            disk.device.controllerKey = controller
            disk.device.unitNumber = unit
            disk.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
            disk.device.backing.fileName = '['+datastore+']'
            disk.device.backing.datastore = Query.get_obj(container, datastore)
            disk.device.backing.diskMode = mode
            disk.device.backing.thinProvisioned = thin
            disk.device.backing.eagerlyScrub = False

        return disk

    @classmethod
    def nic_config(cls, edit=False, **kwargs):
        """
        Method returns configured object for network interface.

        kwargs:
            container (obj):  ContainerView object.
            network (str):    Name of network to add to VM.
            connected (bool): Indicates that the device is currently
                connected. Valid only while the virtual machine is running.
            start_connected (bool):
                Specifies whether or not to connect the device when the
                virtual machine starts.
            allow_guest_control (bool):
                Allows the guest to control whether the connectable device
                is connected.
            driver (str): A str that represents a network adapter driver
            switch_type (str): Use "standard" or "distributed" switch for
                networking.
        Returns:
            nic (obj): A configured object for a Network device.  this should
                be appended to ConfigSpec devices attribute.
        """
        key = kwargs.get('key', None)
        controller = kwargs.get('controller', None)
        container = kwargs.get('container', None)
        mac_address = kwargs.get('mac_address', None)
        network = kwargs.get('network', None)
        connected = kwargs.get('connected', True)
        start_connected = kwargs.get('start_connected', True)
        allow_guest_control = kwargs.get('allow_get_control', True)
        unit = kwargs.get('unit', None)
        address_type = kwargs.get('address_type', 'assigned')
        driver = kwargs.get('driver', 'VirtualVmxnet3')
        switch_type = kwargs.get('switch_type', 'standard')

        nic = vim.vm.device.VirtualDeviceSpec()
        nic.device = getattr(vim.vm.device, driver)()

        if edit:
            nic.operation = 'edit'
            nic.device.key = key
            nic.device.controllerKey = controller
            nic.device.macAddress = mac_address
            nic.device.unitNumber = unit
            nic.device.addressType = address_type
        else:
            nic.operation = 'add'

        if switch_type == 'distributed':
            network_obj = Query.get_obj(container, network)
            dvs = network_obj.config.distributedVirtualSwitch
            criteria = vim.dvs.PortCriteria()
            criteria.connected = False
            criteria.inside = True
            criteria.portgroupKey = network_obj.key
            dvports = dvs.FetchDVPorts(criteria)

            if dvports:
                # pylint: disable=line-too-long
                nic.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
                nic.device.backing.port = vim.dvs.PortConnection()
                nic.device.backing.port.portgroupKey = dvports[0].portgroupKey
                nic.device.backing.port.switchUuid = dvports[0].dvsUuid
                nic.device.backing.port.portKey = dvports[0].key
            else:
                cls.logger.error(
                    'No available distributed virtual port found, so network config failed!'
                )
                cls.logger.debug('%s', dvports)

        elif switch_type == 'standard':
            nic.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
            nic.device.backing.network = Query.get_obj(container, network)
            nic.device.backing.deviceName = network

        nic.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        nic.device.connectable.connected = connected
        nic.device.connectable.startConnected = start_connected
        nic.device.connectable.allowGuestControl = allow_guest_control

        return nic

    def create(self, folder, datastore, pool, **config):
        """
        Method creates the VM.

        Args:
            folder (obj):    Folder object where the VM will reside
            pool (obj):      ResourcePool object
            datastore (str): Datastore for vmx files
            config (dict):   A dict containing vim.vm.ConfigSpec attributes
        Returns:
            result (bool): Result of task_monitor
        """

        vmxfile = vim.vm.FileInfo(vmPathName='[' + datastore + ']')
        config.update({'files' : vmxfile})
        task = folder.CreateVM_Task(config=vim.vm.ConfigSpec(**config), pool=pool)

        self.logger.info('%s', config['name'])
        self.logger.debug('%s %s %s %s', folder, datastore, pool, config)

        result = Tasks.task_monitor(task, False)
        return result

    def clone(self, folder, host, vm_name, config):
        """
        Method clones a new VM from template

        Args:
            folder (obj): Managed Object Reference to folder where VM will reside
            host (obj): Managed Object Reference to VM
            vm_name (str): Name of VM created
            config (dict): A dict containing vim.vm.ConfigSpec attributes
        Returns:
            result (bool): Result of task_monitor
        """
        self.logger.info('%s from %s', vm_name, host.name)

        task = host.CloneVM_Task(folder=folder, name=vm_name, spec=config)
        result = Tasks.task_monitor(task, True, host)
        return result

    def reconfig(self, host, **config):
        """
        Method reconfigures a VM.

        Args:
            host (obj):    VirtualMachine object
            config (dict): A dictionary of vim.vm.ConfigSpec attributes and
                their values.
        Returns:
            result (bool): Result of task_monitor
        """

        self.logger.debug('%s %s', host.name, config)
        task = host.ReconfigVM_Task(vim.vm.ConfigSpec(**config))
        result = Tasks.task_monitor(task, True, host)
        return result


    def power(self, host, state):
        """
        Method manages power states.

        Args:
            host (obj):  VirtualMachine object
            state (str): options are: on,off,reset,rebootshutdown
        """
        self.logger.info('%s %s', host.name, state)
        if state == 'off':
            Tasks.task_monitor(host.PowerOff(), True, host)

        if state == 'on':
            Tasks.task_monitor(host.PowerOn(), True, host)

        if state == 'reset':
            Tasks.task_monitor(host.Reset(), True, host)

        if state == 'reboot':
            Tasks.task_monitor(host.RebootGuest(), True, host)

        if state == 'shutdown':
            host.ShutdownGuest()


    def mvfolder(self, host, folder):
        """
        Method relocate a VM to another folder.

        Args:
            host (list):   List of VirtualMachine objects
            folder (obj):  Folder object
        """

        self.logger.info('Move VM %s to %s folder', host.name, folder.name)
        task = folder.MoveIntoFolder_Task([host])
        Tasks.task_monitor(task, True, host)

    @classmethod
    def vm_hardware_upgrade(cls, host, version=False, scheduled=False, policy=False):
        """
        Method upgrades vm hardware version.

        Args:
            host (obj): VM object
            version (str): VM hardware version supported by ESX host.
            scheduled (bool): Schedule the upgrade upon reboot
            policy (str): Upgrade policy

        Returns:
            spec (obj): Configuration spec object
        """
        spec = None

        if scheduled:
            spec = vim.vm.ScheduledHardwareUpgradeInfo()
            spec.scheduledHardwareUpgradeStatus = 'pending'

            if not policy:
                spec.upgradePolicy = 'never'
            else:
                spec.upgradePolicy = policy

            if version:
                spec.versionKey = version
        else:
            if version:
                host.UpgradeVM_Task(version)
            else:
                host.UpgradeVM_Task()

        return spec

    @classmethod
    def guestinfo_encoder(cls, data):
        """
        Encode data for vm guestinfo

        Args:
            data (bytes) Encoded data
        Returns:
            str string of base64 gzipped data
        """
        stream = io.BytesIO()
        with gzip.GzipFile(fileobj=stream, mode='wb') as data_stream:
            data_stream.write(data)

        return base64.b64encode(stream.getvalue()).decode('ascii')

    @classmethod
    def guestinfo_decoder(cls, data):
        """
        Decode data for vm guestinfo

        Args:
            data (bytes) Decoded data
        Returns:
            str string of base64 gzipped data
        """

        return gzip.decompress(base64.b64decode(data.encode()))
