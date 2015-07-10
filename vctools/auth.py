#!/usr/bin/python
from __future__ import print_function
#
from getpass import getpass, getuser
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim # pylint: disable=E0611
#
import os
import subprocess

class Auth(object):
    def __init__(self, host=None, port=443):
        """
        Authenication Class.
        :param host:       This string is the vSphere host host.
        :param port:       Port to connect to host.
        """

        self.host = host
        self.port = port
        #
        self.session = None
        self.ticket = None


    def decrypt_gpg_file(self, passwd_file):
        if passwd_file.startswith('~'):
            passwd_file = os.path.expanduser(passwd_file)

        command = ['/usr/bin/gpg', '--quiet', '--decrypt', passwd_file]
        decrypt = subprocess.Popen(command, stdout=subprocess.PIPE)
        output = decrypt.communicate()[0].strip()

        return output


    def login(self, user=None, domain=None, passwd_file=None):
        """
        Login to vSphere host

        :param passwd_file: path to GPG encrypted passwd file
        :param domain:     This is for changing the domain to login if needed.
        :param user:       Username to connect to host.
        """

        if user:
            if domain:
                user = domain + '\\' + user
            else:
                pass
        else:
            if domain:
                user = domain + '\\' + getuser()
            else:
                user = getuser()

        print ('Logging in as %s' % user)

        if passwd_file:
            passwd = self.decrypt_gpg_file(passwd_file)
        else:
            passwd = getpass()

        try:
            self.session = SmartConnect(
                host=self.host, user=user, pwd=passwd, port=self.port
            )

            session_mgr = self.session.content.sessionManager

            print ('Successfully logged into %s:%s' % (
                self.host, self.port)
            )
            print()
            self.ticket = session_mgr.AcquireCloneTicket()

            passwd = None

        except vim.fault.InvalidLogin as loginerr:
            user = None
            passwd = None
            print ('error: %s' % (loginerr))


    def logout(self):
        Disconnect(self.session)
        print ('\nlog out successful')

