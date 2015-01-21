#!/usr/bin/python
from __future__ import print_function
#
from getpass import getpass, getuser
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim # pylint: disable=E0611


class Auth(object):
    def __init__(self, host=None, port=443, domain='adlocal', user=None,
                 passwd=None):
        """
        Authenication Class.
        :param host:       This string is the vSphere host host.
        :param port:       Port to connect to host.
        :param domain:     This is for changing the domain to login if needed.
        :param user:       Username to connect to host.
        :param passwd:     Password to connect to host.
        """

        self.host = host
        self.port = port
        self.domain = domain
        self.user = user
        self.passwd = passwd
        #
        self.session = None
        self.ticket = None


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
                self.user = self.domain + '\\' + getuser()
            else:
                self.user = getuser()

        print ('Logging in as %s' % self.user)

        if not self.passwd:
            passwd = getpass()

        try:
            self.session = SmartConnect(
                host=self.host, user=self.user, pwd=passwd, port=self.port
            )

            session_mgr = self.session.content.sessionManager

            print ('Successfully logged into %s:%s' % (
                self.host, self.port)
            )
            self.ticket = session_mgr.AcquireCloneTicket()

            passwd = None

        except vim.fault.InvalidLogin as loginerr:
            self.user = None
            passwd = None
            print ('error: %s' % (loginerr))


    def logout(self):
        Disconnect(self.session)

        print ('log out successful')

