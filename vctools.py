#!/usr/bin/python
import os
import subprocess
import sys
import yaml
import argparse
#
from pyVmomi import vim
from vctools.auth import Auth
from vctools.query import Query
from vctools.vmconfig import VMConfig
from vctools.console import Console

class VCTools(object):
    def __init__(self):
        self.clusters = None
        self.devices = []
        self.folders = None

        # vmrc remote console args
        self.vmrc_path = os.path.expanduser("~/vmware-console/plugins/")
        self.vmrc = 'vmware-vmrc'


    def options(self):
        """argparse command line options."""

        parser = argparse.ArgumentParser(
            description='vCenter Tools CLI'
        )

        # vc (parent)
        vc_parser = argparse.ArgumentParser(add_help=False)
        vc_parser.add_argument(
            'vc',
            help = 'vCenter host'
        )

        # subparser
        subparsers = parser.add_subparsers(metavar='')

        # TODO
        # clone
        #clone_parser = subparsers.add_parser(
        #    'clone', parents=[vc_parser],
        #    help = 'Clone Virtual Machines'
        #)
        #clone_parser.set_defaults(cmd='clone')

        # TODO
        # console
        console_parser = subparsers.add_parser(
            'console', parents=[vc_parser],
            help = 'Generate CLI Console Url'
        )
        console_parser.set_defaults(cmd='console')
        console_parser.add_argument(
           '--name',
            help = 'name attribute of Virtual Machine object.'
        )
        console_parser.add_argument(
           '--datacenter', default='Linux',
           help = 'vCenter Datacenter. default: %(default)s'
        )

        # create
        create_parser = subparsers.add_parser(
            'create', parents=[vc_parser],
            help = 'Create Virtual Machines'
        )
        create_parser.set_defaults(cmd='create')

        create_parser.add_argument(
           'config', type=file,
            help = 'YaML config for creating new Virtual Machines.'
        )

        # TODO
        # power
        #power_parser = subparsers.add_parser(
        #    'power', parents=[vc_parser],
        #    help = 'Power Management for Virtual Machines'
        #)
        #power_parser.set_defaults(cmd='power')

        # query
        query_parser = subparsers.add_parser(
            'query', parents=[vc_parser], 
            help = 'Query Info'
        )
        query_parser.set_defaults(cmd='query')

        query_parser.add_argument(
           '--datastores', action='store_true',
            help = 'Returns information about Datastores.'
        )

        query_parser.add_argument(
           '--vms', action='store_true',
            help = 'Returns information about Virtual Machines.'
        )

        query_parser.add_argument(
           '--folders', action='store_true',
            help = 'Returns information about Folders.'
        )
        
        query_parser.add_argument(
           '--networks', action='store_true',
            help = 'Returns information about Networks.'
        )

        query_parser.add_argument(
           '--clusters', action='store_true',
            help = 'Returns information about ComputeResources.'
        )

        query_parser.add_argument(
           '--cluster',
            help = 'vCenter ComputeResource.'
        )

        query_parser.add_argument(
           '--datacenter', default='Linux',
            help = 'vCenter Datacenter. default: %(default)s'
        )


        # TODO
        # reconfig
        #reconfig_parser = subparsers.add_parser(
        #    'reconfig', parents=[vc_parser],
        #    help = 'Reconfig Virtual Machines'
        #)
        #reconfig_parser.set_defaults(cmd='reconfig')

        self.opts = parser.parse_args()
        self.help = parser.print_help


    def create_containers(self):
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


    def main(self):
        self.options()

        self.auth = Auth(self.opts.vc)
        self.auth.login()

        self.query = Query()
        vmcfg = VMConfig()
        console = Console()

        self.create_containers()

        if self.opts.cmd == 'console':
            if self.opts.name:
                vmid = self.query.get_vmid_by_name(
                    self.datacenters.view, self.opts.datacenter,
                    self.opts.name
                )

                print 'enter in this url into any browser.'
                print console.generate_url(
                    self.opts.vc, vmid, self.opts.name, self.opts.vc, 
                    self.auth.ticket
                )

                #command = '%s -h %s -u %s -M %s' % (
                #        self.vmrc, self.opts.vc, self.auth.user, vmid
                #)

                #os.chdir(self.vmrc_path)
                #subprocess.call(command.split())


        if self.opts.cmd == 'create':
            spec = yaml.load(self.opts.config)
            datastore = spec['config']['datastore']

            cluster = self.query.get_obj(
                self.clusters.view, spec['vcenter']['cluster']
            )

            pool = cluster.resourcePool

            folder = self.query.get_obj(
                self.folders.view, spec['vcenter']['folder']
            )

            # convert kb to gb 
            gb = 1024*1024

            # TODO: increase 4 disk limit
            for scsi, disk in enumerate(spec['devices']['disks']):
                # setup the first four disks on a separate scsi controller
                self.devices.append(vmcfg.scsi_config(scsi))
                self.devices.append(
                    vmcfg.disk_config(
                        cluster.datastore, datastore, disk*gb, unit = scsi
                    )
                )

            for nic in spec['devices']['nics']:
                self.devices.append(vmcfg.nic_config(cluster.network, nic))

            self.devices.append(vmcfg.cdrom_config())
           
            vmcfg.create(folder, pool, *self.devices, **spec['config'])


        if self.opts.cmd == 'query':
            if self.opts.datastores:
                self.query.list_datastore_info(
                    self.clusters.view, self.opts.cluster
                )

            if self.opts.folders:
                folders = self.query.list_obj_attrs(self.folders, 'name')
                folders.sort()
                for folder in folders:
                    print folder

            if self.opts.clusters:
                clusters = self.query.list_obj_attrs(self.clusters, 'name')
                clusters.sort()
                for cluster in clusters:
                    print cluster
            
            if self.opts.networks:
                cluster = self.query.get_obj(
                    self.clusters.view, self.opts.cluster
                )
                networks =  self.query.list_obj_attrs(
                    cluster.network, 'name', view = False
                )
                networks.sort()
                for net in networks:
                    print net

            if self.opts.vms:
                vms = self.query.list_vm_info(
                        self.datacenters.view, self.opts.datacenter
                )
                for key, value in vms.iteritems():
                    print key, value



if __name__ == '__main__':
    vc = VCTools()
    sys.exit(vc.main())
