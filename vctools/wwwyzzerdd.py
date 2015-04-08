#!/usr/bin/python
# pylint: disable=no-name-in-module,no-self-use,too-many-public-methods,unused-argument
"""Interactive module for vctools."""
from __future__ import print_function
from cmd import Cmd
from pyVmomi import vim
from vctools.auth import Auth
from vctools.vmconfig import VMConfig
from vctools.query import Query


def check_auth(func):
    """Decorator used to verify authenticated session."""
    def _check(self, *args, **kwargs):
        """Checks to see if class attribute exists."""
        if self.auth:
            return func(self, *args, **kwargs)
        else:
            print('Error: Please login first.')
    return _check


class Wwwyzzerdd(Cmd):
    """
    It's a Wwwyzzerdd! An interactive wizard for vctools.
    """

    def __init__(self, intro='wwwyzzerdd!', prompt='# ', ruler='_'):
        Cmd.__init__(self)
        self.auth = None
        self.host = None
        self.intro = intro
        self.prompt = prompt
        self.ruler = ruler

    def default(self, arg):
        print('Error %s: Type "ls" for a list. or "?" for help' % (arg))

    def do_connect(self, args):
        """Connect to vcenter.\nUsage: connect <hostname>"""
        if not args:
            print('Error: Please enter in a hostname as an argument.')
        else:
            self.auth = Auth(args)
            self.auth.login()

            if self.auth.ticket:
                self.host = args
                # show the short hostname in prompt
                self.prompt = '(%s)$ ' % (self.host.split('.')[0])

    def do_query(self, args):
        """ Subcategory of command options for querying info."""
        query_cmds = QueryCMDs(self.auth, self.host)
        query_cmds.cmdloop()

    def do_create(self, args):
        """ Subcategory of command options for creating new objects."""
        create_cmds = CreateCMDs(self.auth, self.host)
        create_cmds.cmdloop()

    @check_auth
    def do_logout(self, args):
        """ Logout of system."""
        self.auth.logout()

    def do_exit(self, args):
        """ Exit interactive mode."""
        if self.auth:
            self.auth.logout()
            return True
        else:
            return True

    def do_ls(self, args):
        """ The command we know and love."""
        cmds = []
        names = self.get_names()
        names.sort()
        for name in names:
            if name[:3] == 'do_':
                cmd = name[3:]
                cmds.append(cmd)

        print(' '.join(cmds))


class CreateCMDs(Cmd):
    """ Subcategory of command options for creating new objects."""
    def __init__(self, auth, host):
        Cmd.__init__(self)
        self.auth = auth
        self.host = host
        self.vmcfg = VMConfig()
        self.ruler = '_'
        if self.auth:
            self.prompt = '(create)(%s)$ ' % (self.host.split('.')[0])
        else:
            self.prompt = '(create) # '

    def do_back(self, args):
        """ Return to the main menu."""
        return True

    def do_ls(self, args):
        """ The command we know and love."""
        cmds = []
        names = self.get_names()
        names.sort()
        for name in names:
            if name[:3] == 'do_':
                cmd = name[3:]
                cmds.append(cmd)

        print(' '.join(cmds))

class QueryCMDs(Cmd):
    """ Subcategory of command options for querying info."""
    def __init__(self, auth, host):
        Cmd.__init__(self)
        self.auth = auth
        self.host = host
        self.query = Query()
        self.ruler = '_'
        if self.auth:
            self.prompt = '(query)(%s)$ ' % (self.host.split('.')[0])
        else:
            self.prompt = '(query) # '

    def do_back(self, args):
        """ Return to the main menu."""
        return True

    def do_ls(self, args):
        """ The command we know and love."""
        cmds = []
        names = self.get_names()
        names.sort()
        for name in names:
            if name[:3] == 'do_':
                cmd = name[3:]
                cmds.append(cmd)

        print(' '.join(cmds))

    @check_auth
    def do_networks(self, args):
        """Show networks in cluster.\n  networks <cluster>"""
        if not args:
            print('Error: please enter cluster name.')
        else:
            cluster_container = self.query.create_container(
                self.auth.session, self.auth.session.content.rootFolder,
                [vim.ComputeResource], True
            )
            cluster = self.query.get_obj(
                cluster_container.view, args
            )
            networks = self.query.list_obj_attrs(
                cluster.network, 'name', view=False
            )
            networks.sort()
            for net in networks:
                print(net)

    @check_auth
    def do_datastores(self, args):
        """Show datastores in cluster.\n  usage: datastores <cluster>"""
        if not args:
            print('please enter cluster name.')
        else:
            cluster_container = self.query.create_container(
                self.auth.session, self.auth.session.content.rootFolder,
                [vim.ComputeResource], True
            )
            self.query.list_datastore_info(
                cluster_container.view, args
            )

    @check_auth
    def do_folders(self, datacenter):
        """Show folders in datacenter.\n  folders <datacenter>"""
        if not datacenter:
            print('please enter datacenter name.')
        else:
            datacenter_container = self.query.create_container(
                self.auth.session, self.auth.session.content.rootFolder,
                [vim.Datacenter], True
            )
            folders = self.query.list_vm_folders(
                datacenter_container.view, datacenter
            )
            folders.sort()
            for folder in folders:
                print(folder)

    @check_auth
    def do_datacenters(self, args):
        """Show available datacenters.\n  datacenters"""

        datacenter_container = self.query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.Datacenter], True
        )
        datacenters = self.query.list_obj_attrs(datacenter_container, 'name')
        datacenters.sort()
        for datacenter in datacenters:
            print(datacenter)

    @check_auth
    def do_clusters(self, args):
        """
        show available clusters.

        usage: clusters
        """

        cluster_container = self.query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.ComputeResource], True
        )
        clusters = self.query.list_obj_attrs(cluster_container, 'name')
        clusters.sort()
        for cluster in clusters:
            print(cluster)

