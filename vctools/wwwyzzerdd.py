#!/usr/bin/python
"""interactive module for vctools."""
from __future__ import print_function
from cmd import Cmd
# pylint: disable=no-name-in-module
from pyVmomi import vim
from vctools.auth import Auth
from vctools.query import Query

# pylint: disable=no-self-use
# pylint: disable=too-many-public-methods
# pylint: disable=unused-argument

def check_auth(func):
    """decorator used to verify authenticated session."""
    def _check(self, *args, **kwargs):
        """checks to see if class attribute exists."""
        if Wwwyzzerdd.auth:
            return func(self, *args, **kwargs)
        else:
            print('Please login first.')
    return _check


class Wwwyzzerdd(Cmd):
    """
    It's a Wwwyzzerdd! An interactive wizard for vctools.
    """

    def __init__(self, intro='wwwyzzerdd!', prompt='#'):
        Cmd.__init__(self)
        self.intro = intro
        self.prompt = prompt
        Wwwyzzerdd.auth = None

    def default(self, arg):
        print('%s: Invalid command. Type "help" for a list.' % (arg))

    def do_connect(self, args):
        """
        connect to vcenter.

        usage: connect <hostname>
        """
        if not args:
            print('please enter host')
        else:
            Wwwyzzerdd.auth = Auth(args)
            Wwwyzzerdd.auth.login()

            if Wwwyzzerdd.auth.ticket:
                self.prompt = '$'

    def do_query(self, args):
        """ query sub-category."""
        query_cmds = QueryCMDs()
        query_cmds.cmdloop()

    def do_ticket(self, args):
        """ displays current login ticket info."""
        if self.auth:
            print(self.auth.ticket)
        else:
            print(None)

    def do_logout(self, args):
        """ logout of system."""
        Wwwyzzerdd.auth.logout()

    def do_exit(self, args):
        """ exit interactive mode."""
        if self.auth:
            self.auth.logout()
            return True
        else:
            return True


class QueryCMDs(Cmd):
    """ sub category of cmd options for querying info."""
    def __init__(self, intro='query commands', prompt='(query)'):
        Cmd.__init__(self)
        self.query = Query()
        self.intro = intro
        self.prompt = prompt

    def do_back(self, args):
        """ go back to main menu."""
        return True

    @check_auth
    def do_networks(self, args):
        """
        show networks associated with cluster.

        usage: networks <cluster>
        """
        if not args:
            print('please enter cluster name.')
        else:
            cluster_container = self.query.create_container(
                Wwwyzzerdd.auth.session,
                Wwwyzzerdd.auth.session.content.rootFolder,
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
        """
        show datastores associated with cluster.

        usage: datastores <cluster>
        """
        if not args:
            print('please enter cluster name.')
        else:
            cluster_container = self.query.create_container(
                Wwwyzzerdd.auth.session,
                Wwwyzzerdd.auth.session.content.rootFolder,
                [vim.ComputeResource], True
            )
            self.query.list_datastore_info(
                cluster_container.view, args
            )

    @check_auth
    def do_folders(self, datacenter):
        """
        show available folders.

        usage: folders <datacenter>
        """
        if not datacenter:
            print('please enter datacenter name.')
        else:
            datacenter_container = self.query.create_container(
                Wwwyzzerdd.auth.session, Wwwyzzerdd.auth.session.content.rootFolder,
                [vim.Datacenter], True
            )
            folders = self.query.list_vm_folders(datacenter_container.view, datacenter)
            folders.sort()
            for folder in folders:
                print(folder)

    @check_auth
    def do_datacenters(self, args):
        """
        show available datacenters

        usage: datacenters
        """

        datacenter_container = self.query.create_container(
            Wwwyzzerdd.auth.session, Wwwyzzerdd.auth.session.content.rootFolder,
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
            Wwwyzzerdd.auth.session, Wwwyzzerdd.auth.session.content.rootFolder,
            [vim.ComputeResource], True
        )
        clusters = self.query.list_obj_attrs(cluster_container, 'name')
        clusters.sort()
        for cluster in clusters:
            print(cluster)

