#!/usr/bin/python

class Console(object):
    def __init__(self):
        pass
    def generate_url(self, vc, vmid, name, host, ticket):
        return 'http://%s:7331/console/?vmId=%s&vmName=%s&host=%s&sessionTicket=%s' % (
            vc, vmid, name, host, ticket)

