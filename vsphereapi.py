#!/usr/bin/python
from __future__ import print_function

from pyVim import connect
from pyVmomi import vim

import getpass

class vSphereAPI(object):
    def __init__(self, datacenter=None, port=443, domain='adlocal', user=None, passwd=None):
        self.datacenter = datacenter
        self.port = port
        self.domain = domain
        self.user = user
        self.passwd = passwd
        self.scsiKey = None


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
            self.dcc = connect.SmartConnect( 
                host=self.datacenter, user=self.user, pwd=passwd, port=self.port 
            )

            self.content = self.dcc.content
            self.sessionManager = self.content.sessionManager
            self.sessionKey = self.sessionManager.currentSession.key

            print ('successfully logged into %s:%s as user %s' % (self.datacenter, self.port, self.user))

            passwd = None


        except vim.fault.InvalidLogin as loginerr:
            self.user = None
            passwd = None
            print ('error: %s' % (loginerr))


    def containerObj(self, *args):
        """ 
        Wrapper function for creating objects inside CreateContainerView.
        """

        view = self.content.viewManager.CreateContainerView

        obj = view( *args )

        return obj


    def getObj(self, vimType, name):
        """ 
        returns an object inside of vimtype if it matches name
        """

        obj = self.containerObj( self.content.rootFolder, vimType, True )

        for obj in obj.view:
            if obj.name == name:
                return obj
            else:
                print ('%s not found in %s' % (name, vimType))


    def listObjNames(self, vimType):
        """
        returns a list of object.name inside of vimType
        """

        obj = self.containerObj( self.content.rootFolder, vimType, True )

        return [vm.name for vm in obj.view]


    def scsiConfig(self, sharedBus = 'noSharing'):

        scsi = vim.vm.device.VirtualDeviceSpec()
        scsi.operation = 'add'

        scsi.device = vim.vm.device.ParaVirtualSCSIController()
        scsi.device.sharedBus = sharedBus

        # grab defined key so devices can use it to connect to it.
        self.scsiKey = scsi.device.key

        return scsi


    def cdromConfig(self):
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

    def diskConfig(self, datastore, sizeKB, unit = 0, mode = 'persistent', thin = True):
        """
        Method returns configured VirtualDisk object

        :param datastore: [datastore] where the disk will reside.
        :param sizeKB: int(sizeKB) of disk in kilobytes
        :param unit: unitNumber of device.  
        :param mode: The disk persistence mode. Valid modes are:
                     persistent
                     independent_persistent
                     independent_nonpersistent
                     nonpersistent
		     undoable
                     append 
        :param thin: enable thin provisioning
        """

        disk = vim.vm.device.VirtualDeviceSpec()
        disk.operation = 'add'
        disk.fileOperation = 'create'

        disk.device = vim.vm.device.VirtualDisk()
        disk.device.capacityInKB = sizeKB
        # controllerKey is tied to SCSI Controller
        disk.device.controllerKey = self.scsiKey
        disk.device.unitNumber = unit

        disk.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
        disk.device.backing.fileName = '['+datastore+']'
        disk.device.backing.datastore = self.getObj([vim.Datastore], datastore)
        disk.device.backing.diskMode = mode
        disk.device.backing.thinProvisioned = thin
        disk.device.backing.eagerlyScrub = False

        return disk

    def nicConfig(self, network):
        """
        Method returns configured object for VirtualDevice() network interface.

        :param network: network to add
        """ 

        nic = vim.vm.device.VirtualDeviceSpec()
        nic.operation = 'add'

        nic.device = vim.vm.device.VirtualVmxnet3()

        nic.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
        nic.device.backing.network = self.getObj([vim.Network], network)
        nic.device.backing.deviceName = network

        nic.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        nic.device.connectable.connected = True
        nic.device.connectable.startConnected = True
        nic.device.connectable.allowGuestControl = True

        return nic


    def createVM(self, name, folder, network, datastore, sizeKB, cpu, memoryMB, pool, hwVer='vmx-08', guestId='rhel6_64Guest'):
       
        scsi = self.scsiConfig() 
        cdrom = self.cdromConfig()
        nic = self.nicConfig(network)
        disk = self.diskConfig(datastore, sizeKB)

        vmxfile = vim.vm.FileInfo(
            vmPathName='['+datastore+']'
        )

        config = vim.vm.ConfigSpec(
            name=name,
            version=hwVer,
            guestId=guestId,
            files=vmxfile,
            numCPUs=cpu,
            memoryMB=memoryMB,
            deviceChange=[scsi, cdrom, nic, disk],
        )

        print (
            """
            Creating VM using these values:
            name: %s
            cpu: %s
            mem: %s
            nic: %s
            disk: %s KB
            datastore: %s

            It'll be done shortly.
            """ % (name, cpu, memoryMB, network, sizeKB, datastore)
        )

        self.folder = self.getObj([vim.Folder], folder)
        self.folder.CreateVM_Task(config=config, pool=self.getObj([vim.ResourcePool], pool))
        
        print ('all done')



