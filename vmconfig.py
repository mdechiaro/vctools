#!/usr/bin/python
from __future__ import print_function

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim # pylint: disable=E0611

import getpass
import random

class VMConfig(object): 
    """ 
    Class goal is to simplify VM builds outside of using the client or Web App.
    Class can handle setting up a complete VM with multiple devices attached.  
    It can also handle the addition of mutiple disks attached to multiple SCSI 
    controllers, as well as multiple network interfaces.    
    """

    def __init__(self, datacenter=None, port=443, domain='adlocal', 
                 user=None, passwd=None):
        """
        Define our class attributes here.

        :param datacenter: This string is the vSphere datacenter host.
        :param port:       Port to connect to host.
        :param domain:     This is for changing the domain to login if needed.
        :param user:       Username to connect to host.
        :param passwd:     Password to connect to host.  
        """

        self.datacenter = datacenter
        self.port = port
        self.domain = domain
        self.user = user
        self.passwd = passwd
        #
        self.dcc = None
        self.content = None
        self.session_manager = None 
        self.session_key = None
        self.scsi_key = None


    def login(self):
        """
        Login to vSphere host
        """

        if self.user:
            if self.domain:
                self.user = self.domain + '\\' + self.user
            else:
                pass
        else:
            if self.domain:
                self.user = self.domain + '\\' + getpass.getuser()
            else:
                self.user = getpass.getuser()

        if not self.passwd:
            passwd = getpass.getpass()

        try:
            self.dcc = SmartConnect( 
                host=self.datacenter, user=self.user, pwd=passwd, port=self.port 
            )

            self.content = self.dcc.content
            self.session_manager = self.content.sessionManager
            self.session_key = self.session_manager.currentSession.key

            print ('successfully logged into %s:%s as user %s' % (
                self.datacenter, self.port, self.user)
            )

            passwd = None

        except vim.fault.InvalidLogin as loginerr:
            self.user = None
            passwd = None
            print ('error: %s' % (loginerr))


    def logout(self):
        Disconnect(self.dcc)

        print ('log out successful')


    def container_obj(self, *args):
        """ 
        Wrapper function for creating objects inside CreateContainerView.
        """

        view = self.content.viewManager.CreateContainerView

        obj = view( *args )

        return obj


    def get_obj(self, arg, name):
        """ 
        Returns an object inside of arg if it matches name. 

        :param arg: [vim.arg] (i.e. [vim.Datastore])
        :param name: Name to match
        """

        obj = self.container_obj( self.content.rootFolder, arg, True )

        for obj in obj.view:
            if obj.name == name:
                return obj
            else:
                print ('%s not found in %s' % (name, arg))


    def list_obj_names(self, arg):
        """
        Returns a list of string names inside of arg

        :param arg: [vim.arg] (i.e. [vim.Network])
        """

        obj = self.container_obj( self.content.rootFolder, arg, True )

        return [vm.name for vm in obj.view]


    def scsi_config(self, bus_number = 0, shared_bus = 'noSharing'):
        """
        Method creates a SCSI Controller on the VM

        :param busNumber: Bus number associated with this controller.
        :param sharedBus: Mode for sharing the SCSI bus. 
                          physicalSharing
                          virtualSharing
                          noSharing
        """

        # randomize key for multiple scsi controllers
        key = int(random.uniform(-1, -100))

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


    def disk_config(self, datastore, size, unit = 0, mode = 'persistent', 
                    thin = True):
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
        disk.device.backing.datastore = self.get_obj([vim.Datastore], datastore)
        disk.device.backing.diskMode = mode
        disk.device.backing.thinProvisioned = thin
        disk.device.backing.eagerlyScrub = False

        return disk


    def nic_config(self, network):
        """
        Method returns configured object for network interface.

        :param network: string network to add to VM.
        """ 

        nic = vim.vm.device.VirtualDeviceSpec()
        nic.operation = 'add'

        nic.device = vim.vm.device.VirtualVmxnet3()

        nic.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
        nic.device.backing.network = self.get_obj([vim.Network], network)
        nic.device.backing.deviceName = network

        nic.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        nic.device.connectable.connected = True
        nic.device.connectable.startConnected = True
        nic.device.connectable.allowGuestControl = True

        return nic


    def create_vm(self, hostname, version, guest_id, folder, datastore, cpu, 
                  memory, pool, *devices):
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

            It'll be done shortly.
            """ % (hostname, cpu, memory, datastore)
        )

        folder_obj = self.get_obj([vim.Folder], folder)

        folder_obj.CreateVM_Task(
            config=config, 
            pool=self.get_obj([vim.ResourcePool], pool)
        )
        
        print ('all done')
