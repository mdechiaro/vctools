#!/usr/bin/python
"""interactive module for vctools."""
from __future__ import print_function
from cmd import Cmd
# pylint: disable=no-name-in-module
from pyVmomi import vim
from vctools.auth import Auth
from vctools.vmconfig import VMConfig
from vctools.query import Query

# pylint: disable=no-self-use
# pylint: disable=too-many-public-methods
# pylint: disable=unused-argument
class Wwwyzzerdd(Cmd):
    """
    It's a Wwwyzzerdd! An interactive wizard for vctools.
    """

    def __init__(self, intro='wwwyzzerdd!', prompt='# '):
        Cmd.__init__(self)
        Wwwyzzerdd.auth = None
        self.intro = intro
        self.prompt = prompt

    def default(self, arg):
        print('%s: Invalid command. Type "help" for a list.' % (arg))

    def do_connect(self, vcenter):
        """ connect to vcenter."""
        Wwwyzzerdd.auth = Auth(vcenter)
        Wwwyzzerdd.auth.login()

    def do_query(self, args):
        """ query sub-category."""
        query_cmds = QueryCMDs()
        query_cmds.cmdloop()

    def do_ticket(self, args):
        if self.auth:
            print(self.auth.ticket)
        else:
            print(None)

    def do_exit(self, args):
        """ exit interactive mode."""
        if self.auth:
            self.auth.logout()
            return True
        else:
            return True


class QueryCMDs(Cmd):
    """ sub category of cmd options for querying info."""
    def __init__(self, intro='query commands', prompt='(query) # '):
        Cmd.__init__(self)
        self.query = Query()
        self.intro = intro
        self.prompt = prompt

    def do_back(self, args):
        """ exit interactive mode."""
        return True

    def do_networks(self, args):
        """ show networks associated with cluster."""
        cluster_container = self.query.create_container(
            Wwwyzzerdd.auth.session, Wwwyzzerdd.auth.session.content.rootFolder,
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

    def do_datastores(self, args):
        """ show datastores associated with cluster."""
        cluster_container = self.query.create_container(
            Wwwyzzerdd.auth.session, Wwwyzzerdd.auth.session.content.rootFolder,
            [vim.ComputeResource], True
        )
        self.query.list_datastore_info(
            cluster_container.view, args
        )

    def do_folders(self, args):
        """ show available folders."""
        folder_container = self.query.create_container(
            Wwwyzzerdd.auth.session, Wwwyzzerdd.auth.session.content.rootFolder,
            [vim.Folder], True
        )
        folders = self.query.list_obj_attrs(folder_container, 'name')
        folders.sort()
        for folder in folders:
            print(folder)

    def do_clusters(self, args):
        """ show available clusters."""
        cluster_container = self.query.create_container(
            Wwwyzzerdd.auth.session, Wwwyzzerdd.auth.session.content.rootFolder,
            [vim.ComputeResource], True
        )
        clusters = self.query.list_obj_attrs(cluster_container, 'name')
        clusters.sort()
        for cluster in clusters:
            print(cluster)

