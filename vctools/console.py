#!/usr/bin/python
import re


class Console(object):
    def __init__(self):
        pass


    def mkthumbprint(self, ticket):
        """
        This method uses the information in a ticket to generate a thumbprint.
        The string is split on --, and uses the second part to convert to the
        appropriate format.

        :param ticket: vim.SessionManager.AcquireCloneTicket()
        """

        thumbprint = re.sub(r'tp-', '', ticket.split('--')[1])
        thumbprint = re.sub(r'-', ':', thumbprint)
        return thumbprint


    def mkurl(self, vmid, name, vc, ticket, thumbprint):
        """
        We have a Tomcat broker (web) which has a different hostname than our
        vCenter, so we need to account for that.  The hostname appends -web to
        vc hostname.
        """

        host, domain, tld = vc.split('.')
        host = host + '-web'
        web = '.'.join((host, domain, tld))

        return 'http://%s:7331/console/?vmId=%s&vmName=%s&host=%s&sessionTicket=%s&thumbprint=%s' % (
            web, vmid, name, vc, ticket, thumbprint)

