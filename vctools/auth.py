#!/usr/bin/python
"""Authentication Class for vctools."""
# vim: ts=4 sw=4 et
from __future__ import print_function
import os
import subprocess
from getpass import getpass, getuser
import ssl
import requests
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim # pylint: disable=E0611
from vctools import Logger

# disable SSL warnings
requests.packages.urllib3.disable_warnings()

class Auth(Logger):
    """Authentication Class."""
    def __init__(self, host=None, port=443):
        """
        Args:
            host (str): This string is the vSphere host host.
            port (int): Port to connect to host.
        """
        self.host = host
        self.port = port
        self.session = None
        self.ticket = None


    @classmethod
    def decrypt_gpg_file(cls, passwd_file):
        """
        Decrypts a gpg file containing a password for auth.

        Args:
            passwd_file (str): Name of file that contains an encrypted passwd.
                Path should be included if file resides outside of module.
        """
        if passwd_file.startswith('~'):
            passwd_file = os.path.expanduser(passwd_file)

        command = ['/usr/bin/gpg', '--quiet', '--decrypt', passwd_file]
        decrypt = subprocess.Popen(command, stdout=subprocess.PIPE)
        output = decrypt.communicate()[0].strip()

        return output

    def login(self, user=None, passwd=None, domain=None, passwd_file=None, sslcontext=None):
        """
        Login to vSphere host

        Args:
            user (str):        Username
            passwd (str):      Password
            domain (str):      Domain name
            passwd_file (str): Name of file that contains an encrypted passwd.
                Path should be included if file resides outside of module.
            sslcontext (obj):  Can disable SSL verification for Python 2.7.9+
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

        if not passwd:
            if passwd_file:
                passwd = self.decrypt_gpg_file(passwd_file)
            else:
                passwd = getpass()

        try:
            self.session = SmartConnect(
                host=self.host, user=user, pwd=passwd, port=self.port
            )

            session_mgr = self.session.content.sessionManager

            self.ticket = session_mgr.AcquireCloneTicket()
            self.logger.info('%s %s success', user, self.host)

            passwd = None

        # https://www.python.org/dev/peps/pep-0476/
        except ssl.SSLError:
            if sslcontext:
                context = sslcontext
            # disable ssl verification
            elif hasattr(ssl, '_create_unverified_context'):
                context = ssl._create_unverified_context()
                self.session = SmartConnect(
                    host=self.host, user=user, pwd=passwd, port=self.port, sslContext=context
                )
            else:
                raise

        except vim.fault.InvalidLogin:
            user = None
            passwd = None
            raise

    def logout(self):
        """Logout of vSphere."""
        self.logger.info('successful')
        Disconnect(self.session)
