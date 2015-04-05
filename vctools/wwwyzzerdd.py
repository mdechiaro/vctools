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
class WWWYZZERDD(Cmd):
    """
    It's a Wwwyzzerdd! An interactive wizard for vctools.
    """

    def __init__(self, intro='wwwyzzerdd!', prompt='# '):
        Cmd.__init__(self)
        self.auth = None
        self.intro = intro
        self.prompt = prompt
        self.doc_header = 'interactive wizard for vctools.'

    def default(self, arg):
        print('%s: Invalid command. Type "help" for a list.' % (arg))

    def do_connect(self, vcenter):
        """ connect to vcenter."""
        self.auth = Auth(vcenter)
        self.auth.login()

    def do_query(self, args):
        """ query sub-category."""
        query_cmds = QueryCMDs()
        query_cmds.cmdloop()

    def do_create(self, args):
        """ create sub-category."""
        create_cmds = CreateCMDs()
        create_cmds.cmdloop()

    def do_exit(self, args):
        """ exit interactive mode."""
        return True


class QueryCMDs(WWWYZZERDD):
    """ sub category of cmd options for querying info."""
    def __init__(self):
        self.datacenters = None
        self.clusters = None
        self.folders = None
        self.virtual_machines = None
        self.query = Query()
        WWWYZZERDD.__init__(self, intro='query commands', prompt='(query) # ')

    def __call__(self):
        self.datacenters = self.query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.Datacenter], True
        )

        self.clusters = self.query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.ComputeResource], True
        )

        self.folders = self.query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.Folder], True
        )

        self.virtual_machines = self.query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.VirtualMachine], True
        )


    def do_networks(self, cluster):
        """ show networks associated with cluster."""
        cluster = self.query.get_obj(
            self.clusters.view, cluster
        )
        networks = self.query.list_obj_attrs(
            cluster.network, 'name', view=False
        )
        networks.sort()
        for net in networks:
            print(net)

    def do_datastores(self, cluster):
        """ show datastores associated with cluster."""
        self.query.list_datastore_info(
            self.clusters.view, cluster
        )
    def do_folders(self):
        """ show available folders."""
        folders = self.query.list_obj_attrs(self.folders, 'name')
        folders.sort()
        for folder in folders:
            print(folder)

    def do_clusters(self):
        """ show available clusters."""
        clusters = self.query.list_obj_attrs(self.clusters, 'name')
        clusters.sort()
        for cluster in clusters:
            print(cluster)

    # pylint: disable=invalid-name
    def do_VMs(self, datacenter):
        """ show available virtual machines associated with datacenter."""
        vms = self.query.list_vm_info(
            self.datacenters.view, datacenter
        )
        for key, value in vms.iteritems():
            print(key, value)

class CreateCMDs(WWWYZZERDD):
    """ sub category of cmd options for creating virtual machines."""
    def __init__(self):
        self.vmcfg = VMConfig()
        WWWYZZERDD.__init__(self, intro='create a new VM', prompt='(create) # ')
