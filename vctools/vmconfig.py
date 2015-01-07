#!/usr/bin/python
from __future__ import print_function
from random import uniform
from pyVmomi import vim # pylint: disable=E0611
#
from query import Query
#
import requests
import sys

class VMConfig(Query):
    """
    Class simplifies VM builds outside of using the client or Web App.
    Class can handle setting up a complete VM with multiple devices attached.
    It can also handle the addition of mutiple disks attached to multiple SCSI
    controllers, as well as multiple network interfaces.
    """

    def __init__(self):
        """ Define our class attributes here. """
        Query.__init__(self)
        self.scsi_key = None


    def upload_iso(self, host, cookie, datacenter, dest_folder, datastore,
                   iso, verify=False):
        """
        Method uploads iso to dest_folder.

        :param host:        vCenter host
        :param cookie:      Cookie from Service Instance
                            example: auth.session._stub.cookie
        :param datacenter:  Datacenter that has access to the datastore.
        :param dest_folder: Folder that will store the iso.
        :param datastore:   Datastore that will store the iso.
        :param iso:         ISO file
        :param verify:      Enable or disable SSL certificate validation.

        """

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

        data = {iso_name : open(iso, 'rb')}
        params = {'dcPath' : datacenter, 'dsName' : datastore}
        url = 'https://' + host + dest_folder + '/' + iso_name

        response = requests.put(
            url, params=params, cookies=cookie, files=data, verify=verify
        )

        return response.status_code


    def task_monitor(self, task):
        """ method monitors the state of called task and outputs info. """
        while task.info.state == 'running':
            while task.info.progress:
                # Ensure it's an integer before printing, otherwise None
                # Tracebacks appear.
                if isinstance(task.info.progress, int):
                    sys.stdout.write(
                        '\r[' + task.info.state + '] | ' +
                        str(task.info.progress)
                    )
                    sys.stdout.flush()
                    if task.info.progress == 100:
                        sys.stdout.write(
                            '\r[' + task.info.state + '] | ' +
                            str(task.info.progress)
                        )
                        sys.stdout.flush()
                        break
                else:
                    sys.stdout.flush()
                    break

        print()

        if task.info.state == 'error':
            sys.stdout.write(
                '\r[' + task.info.state + '] | ' + task.info.error.msg
            )
            sys.stdout.flush()

        if task.info.state == 'success':
            sys.stdout.write(
                '\r[' + task.info.state + '] | ' +
                'task successfully completed.'
            )
            sys.stdout.flush()

        print()


    def assign_ip(self, ip, mask, gw, domain, dhcp=False, *dns):
        if dhcp:
            nic = vim.vm.customization.AdapterMapping()
            nic.adapter = vim.vm.customization.DhcpIpGenerator()

            return nic
        else:
            nic.adapter = vim.vm.customization.IPSettings()
            nic.adapter.ip = vim.vm.customization.FixedIp()
            nic.adapter.ip.ipAddress = ip
            nic.adapter.subnetMask = mask
            nic.adapter.gateway = gw
            nic.adapter.dnsDomain = domain
            nic.adapter.dnsServerList = list(dns)

            return nic


    def scsi_config(self, bus_number=0, shared_bus='noSharing'):
        """
        Method creates a SCSI Controller on the VM

        :param bus_number: Bus number associated with this controller.
        :param shared_bus: Mode for sharing the SCSI bus.
                           physicalSharing
                           virtualSharing
                           noSharing
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
        self.scsi_key = scsi.device.key

        return scsi


    def cdrom_config(self, datastore=None, iso_path=None):
        """
        Method manages a CD-Rom Virtual Device.  If iso_path is not provided,
        then it will create the device.  Otherwise, it will attempt to mount
        the iso.  Iso must reside inside a datastore.  Use the upload_iso()
        method to use an iso stored locally.

        :param datastore: string name of datastore
        :param iso_path:  path/to/file.iso
        """

        if iso_path and datastore:
            cdrom = vim.vm.device.VirtualDeviceSpec()
            cdrom.operation = 'edit'

            cdrom.device = vim.vm.device.VirtualCdrom()
            # controllerKey is tied to IDE Controller
            cdrom.device.controllerKey = 201
            cdrom.device.unitNumber = 0
            # key is needed to mount the iso, need to verify if this value
            # changes per host, and if so, then logic needs to be added to
            # obtain it
            cdrom.device.key = 3002

            cdrom.device.backing = vim.vm.device.VirtualCdrom.IsoBackingInfo()
            cdrom.device.backing.fileName = '['+ datastore + '] ' + iso_path

            cdrom.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
            cdrom.device.connectable.connected = True
            cdrom.device.connectable.startConnected = True
            cdrom.device.connectable.allowGuestControl = True

            return cdrom

        else:
            cdrom = vim.vm.device.VirtualDeviceSpec()
            cdrom.operation = 'add'

            cdrom.device = vim.vm.device.VirtualCdrom()
            # controllerKey is tied to IDE Controller
            cdrom.device.controllerKey = 201

            cdrom.device.backing = vim.vm.device.VirtualCdrom.RemotePassthroughBackingInfo()
            cdrom.device.backing.exclusive = False

            cdrom.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
            cdrom.device.connectable.connected = False
            cdrom.device.connectable.startConnected = False
            cdrom.device.connectable.allowGuestControl = True

            return cdrom


    def disk_config(self, container, datastore, size, unit=0,
                    mode='persistent', thin=True):
        """
        Method returns configured VirtualDisk object

        :param datastore: string datastore for the disk files location.
        :param size:      integer of disk in kilobytes
        :param unit:      unitNumber of device.
        :param mode:      The disk persistence mode. Valid modes are:
                          persistent
                          independent_persistent
                          independent_nonpersistent
                          nonpersistent
		          undoable
                          append
        :param thin:      enable thin provisioning
        """

        disk = vim.vm.device.VirtualDeviceSpec()
        disk.operation = 'add'
        disk.fileOperation = 'create'

        disk.device = vim.vm.device.VirtualDisk()
        disk.device.capacityInKB = size
        # controllerKey is tied to SCSI Controller
        disk.device.controllerKey = self.scsi_key
        disk.device.unitNumber = unit

        disk.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
        disk.device.backing.fileName = '['+datastore+']'
        disk.device.backing.datastore = self.get_obj(container, datastore)
        disk.device.backing.diskMode = mode
        disk.device.backing.thinProvisioned = thin
        disk.device.backing.eagerlyScrub = False

        return disk


    def nic_config(self, container, network, connected=True,
                   start_connected=True, allow_guest_control=True):
        """
        Method returns configured object for network interface.

        :param network: string network to add to VM.
        """

        nic = vim.vm.device.VirtualDeviceSpec()
        nic.operation = 'add'

        nic.device = vim.vm.device.VirtualVmxnet3()

        nic.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
        nic.device.backing.network = self.get_obj(container, network)
        nic.device.backing.deviceName = network

        nic.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        nic.device.connectable.connected = connected
        nic.device.connectable.startConnected = start_connected
        nic.device.connectable.allowGuestControl = allow_guest_control

        return nic

    def create(self, folder, pool, datastore, *devices, **config):
        """
        Method creates the VM.

        :param folder:    Folder object where the VM will reside
        :param pool:      ResourcePool object
        :param datastore: datastore for vmx files
        :param config:    dictionary of vim.vm.ConfigSpec attributes and their
                          values, excluding devices.
        :param devices:   list of configured devices.  See scsi_config,
                          cdrom_config, and disk_config.
        """

        vmxfile = vim.vm.FileInfo(
            vmPathName='[' + datastore + ']'
        )

        config.update({'files' : vmxfile})
        config.update({'deviceChange' : list(devices)})

        task = folder.CreateVM_Task(
            config=vim.vm.ConfigSpec(**config),
            pool=pool,
        )

        print('Creating VM %s' % config['name'])

        self.task_monitor(task)


    def reconfig(self, host, **config):
        """
        Method reconfigures a VM.

        :param host:      VirtualMachine object
        :param config:    dictionary of vim.vm.ConfigSpec attributes and their
                          values.
        """

        task = host.ReconfigVM_Task(
            vim.vm.ConfigSpec(**config),
        )

        print('Reconfiguring VM %s with %s' % (
            host.name,
            ', '.join("%s=%s" % (key, val) for key, val in config.items())
            )
        )

        self.task_monitor(task)

    # TODO
    def clone(self, hostname, folder, name, **config):
        hostname.CloneVM_Task(
            folder, name, **config
        )

    def power(self, host, state):
        """Method manages power states."""
        if state == 'off':
            self.task_monitor(host.PowerOff())

        if state == 'on':
            self.task_monitor(host.PowerOn())

        if state == 'reset':
            self.task_monitor(host.Reset())
