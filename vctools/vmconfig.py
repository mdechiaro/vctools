#!/usr/bin/python
from __future__ import print_function
from random import uniform
from pyVmomi import vim # pylint: disable=E0611
#
from query import Query


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


    def scsi_config(self, bus_number = 0, shared_bus = 'noSharing'):
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


    @classmethod
    def cdrom_config(cls):
        """
        Method creates a CD-Rom Virtual Device
        """

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


    def disk_config(self, container, datastore, size, unit = 0, 
                    mode = 'persistent', thin = True):
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


    def nic_config(self, container, network):
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
        nic.device.connectable.connected = True
        nic.device.connectable.startConnected = True
        nic.device.connectable.allowGuestControl = True

        return nic


    def create_vm(self, hostname, version, guest_id, folder, container, 
                  datastore, cpu, memory, pool, *devices):
        """
        Method creates the VM.

        :param hostname:  Display name of the virtual machine.
        :param version:   The version string for this virtual machine.
        :param guestId:   Short guest operating system identifier.
        :param folder:    string container for storing and organizing inventory
                          objects.
        :param datastore: string datastore where the vmdk files are stored. 
        :param cpu:       Number of virtual processors in a virtual machine. 
        :param memory:    Size of a virtual machine's memory, in MB. 
        :param pool:      string resource pool.
        :param devices:   list of configured devices.  See scsi_config, 
                          cdrom_config, and disk_config.  
        """

        vmxfile = vim.vm.FileInfo(
            vmPathName='['+datastore+']'
        )

        devices = list(devices)

        config = vim.vm.ConfigSpec(
            name=hostname,
            version=version,
            guestId=guest_id,
            files=vmxfile,
            numCPUs=cpu,
            memoryMB=memory,
            deviceChange=devices,
        )

        print (
            """
            Creating VM using these values:
            name: %s
            cpu: %s
            mem: %s
            datastore: %s
            devices: %s

            It'll be done shortly.
            """ % (hostname, cpu, memory, datastore, len(devices))
        )

        folder_obj = self.get_obj(container, folder)

        folder_obj.CreateVM_Task(
            config=config, 
            pool=self.get_obj(container, pool)
        )
        
        print ('all done')

