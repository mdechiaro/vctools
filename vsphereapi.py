#!/usr/bin/python
from __future__ import print_function

from pyVim import connect
from pyVmomi import vim
from pyVmomi import Iso8601

import getpass

class vSphereAPI(object):
    def __init__(self, datacenter=None, port=443, domain='adlocal', user=None, passwd=None):
        self.datacenter = datacenter
        self.port = port
        self.domain = domain
        self.user = user
        self.passwd = passwd


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


    def diskConfig(self, datastore, sizeKB, mode = 'persistent', thin = True):
        """
        Method returns configured VirtualDisk object

        :param datastore: [datastore] where the disk will reside.
        :param sizeKB: int(sizeKB) of disk in kilobytes
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

        disk.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
        disk.device.backing.fileName = datastore
        disk.device.backing.datastore = self.getObj([vim.Datastore], datastore)
        disk.device.backing.diskMode = mode
        disk.device.backing.thinProvisioned = thin 

        return disk


    def nicConfig(self, network):
        """
        Method returns configured object for VirtualDevice() network interface.

        :param network: network to add
        """ 

        nic = vim.vm.device.VirtualDeviceSpec()
        nic.operation = 'add'

        nic.device = vim.vm.device.VirtualDevice()
        nic.device.deviceInfo = vim.Description()
        nic.device.unitNumber = unit

        nic.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
        nic.device.backing.network = self.getObj([vim.Network], network)
        nic.device.backing.deviceName = network

        nic.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        nic.device.connectable.connected = True
        nic.device.connectable.startConnected = True
        nic.device.connectable.allowGuestControl = True

        return nic

