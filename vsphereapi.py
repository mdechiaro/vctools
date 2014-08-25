#!/usr/bin/python
from __future__ import print_function

from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim
from pyVmomi import  Iso8601

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


    def listVMs(self):
        """ 
        returns a list of VM names.
        """

        obj = self.containerObj( self.content.rootFolder, [vim.VirtualMachine], True )

        return [vm.name for vm in obj.view]


    def getId(self, system):
        """ 
        returns a id of system
        """

        obj = self.containerObj( self.content.rootFolder, [vim.VirtualMachine], True )

        return [vm for vm in obj.view if vm.name in system]



    def listDCs(self):
        """ 
        returns a list of datacenter names.
        """

        obj = self.containerObj( self.content.rootFolder, [vim.Datacenter], True )

        return [dc for dc in obj.view]


    def listDSs(self):
        """ 
        returns a list of datastore names inside of datacenter

        """
   
        obj = self.containerObj( self.content.rootFolder, [vim.Datastore], True )
        
        return [ds.info.name for ds in obj.view]


