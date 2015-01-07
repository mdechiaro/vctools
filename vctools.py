#!/usr/bin/python
from __future__ import print_function
import argparse
import sys
import yaml
#
from pyVmomi import vim
from vctools.auth import Auth
from vctools.console import Console
from vctools.vmconfig import VMConfig
from vctools.query import Query


class VCTools(object):
    def __init__(self):
        self.clusters = None
        self.devices = []
        self.folders = None


    def options(self):
        """argparse command line options."""

        parser = argparse.ArgumentParser(
            description='vCenter Tools CLI'
        )

        # vc (parent)
        vc_parser = argparse.ArgumentParser(add_help=False)
        vc_parser.add_argument(
            'vc',
            help='vCenter host'
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
            help='Generate CLI Console Url'
        )
        console_parser.set_defaults(cmd='console')
        console_parser.add_argument(
           '--name',
            help='name attribute of Virtual Machine object.'
        )
        console_parser.add_argument(
           '--datacenter', default='Linux',
           help='vCenter Datacenter. default: %(default)s'
        )

        # create
        create_parser = subparsers.add_parser(
            'create', parents=[vc_parser],
            help='Create Virtual Machines'
        )
        create_parser.set_defaults(cmd='create')

        create_parser.add_argument(
           'config', type=file,
            help='YaML config for creating new Virtual Machines.'
        )

        # power
        power_parser = subparsers.add_parser(
            'power', parents=[vc_parser],
            help = 'Power Management for Virtual Machines'
        )
        power_parser.set_defaults(cmd='power')

        power_parser.add_argument(
            'power', choices=['on', 'off', 'reset'],
            help = 'change power state of VM'

        )
        power_parser.add_argument(
           '--name',
            help='name attribute of Virtual Machine object.'
        )

        # query
        query_parser = subparsers.add_parser(
            'query', parents=[vc_parser],
            help='Query Info'
        )
        query_parser.set_defaults(cmd='query')

        query_parser.add_argument(
           '--datastores', action='store_true',
            help='Returns information about Datastores.'
        )

        query_parser.add_argument(
           '--vms', action='store_true',
            help='Returns information about Virtual Machines.'
        )

        query_parser.add_argument(
           '--folders', action='store_true',
            help='Returns information about Folders.'
        )

        query_parser.add_argument(
           '--networks', action='store_true',
            help='Returns information about Networks.'
        )

        query_parser.add_argument(
           '--clusters', action='store_true',
            help='Returns information about ComputeResources.'
        )

        query_parser.add_argument(
           '--cluster',
            help='vCenter ComputeResource.'
        )

        query_parser.add_argument(
           '--datacenter', default='Linux',
            help='vCenter Datacenter. default: %(default)s'
        )


        # upload
        upload_parser = subparsers.add_parser(
            'upload', parents=[vc_parser],
            help='Upload File'
        )
        upload_parser.set_defaults(cmd='upload')

        upload_parser.add_argument(
           '--iso',
            help='iso file that needs to be uploaded to vCenter.'
        )

        upload_parser.add_argument(
           '--dest',
            help='destination folder where the iso will reside.'
        )

        upload_parser.add_argument(
           '--datastore', default='ISO_Templates',
            help='datastore where the iso will reside.  default: %(default)s'
        )

        upload_parser.add_argument(
           '--verify-ssl', default=False,
            help='verify SSL certificate. default: %(default)s'
        )

        upload_parser.add_argument(
           '--datacenter', default='Linux',
            help='vCenter Datacenter. default: %(default)s'
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

                thumbprint = console.mkthumbprint(self.auth.ticket)

                print('enter in this url into any browser.')
                command = console.mkurl(
                    vmid, self.opts.name, self.opts.vc, self.auth.ticket,
                    thumbprint
                )
                print(command)


        if self.opts.cmd == 'create':
            spec = yaml.load(self.opts.config)
            datastore = spec['vcenter']['datastore']

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
                        cluster.datastore, datastore, disk*gb, unit=scsi
                    )
                )

            for nic in spec['devices']['nics']:
                self.devices.append(vmcfg.nic_config(cluster.network, nic))

            self.devices.append(vmcfg.cdrom_config())

            vmcfg.create(
                folder, pool, datastore, *self.devices, **spec['config']
            )


        if self.opts.cmd == 'power':
            if self.opts.name:
                host = self.query.get_obj(
                    self.virtual_machines.view, self.opts.name
                )
                print('%s changing power state to %s' % (
                    self.opts.name, self.opts.power
                    )
                )
                vmcfg.power(host, self.opts.power)


        if self.opts.cmd == 'query':
            if self.opts.datastores:
                self.query.list_datastore_info(
                    self.clusters.view, self.opts.cluster
                )

            if self.opts.folders:
                folders = self.query.list_obj_attrs(self.folders, 'name')
                folders.sort()
                for folder in folders:
                    print(folder)

            if self.opts.clusters:
                clusters = self.query.list_obj_attrs(self.clusters, 'name')
                clusters.sort()
                for cluster in clusters:
                    print(cluster)


            if self.opts.networks:
                cluster = self.query.get_obj(
                    self.clusters.view, self.opts.cluster
                )
                networks = self.query.list_obj_attrs(
                    cluster.network, 'name', view=False
                )
                networks.sort()
                for net in networks:
                    print(net)

            if self.opts.vms:
                vms = self.query.list_vm_info(
                        self.datacenters.view, self.opts.datacenter
                )
                for key, value in vms.iteritems():
                    print(key, value)


        if self.opts.cmd == 'upload':
            print('uploading ISO: %s' % (self.opts.iso))
            result = vmcfg.upload_iso(
                self.opts.vc, self.auth.session._stub.cookie,
                self.opts.datacenter, self.opts.dest, self.opts.datastore,
                self.opts.iso, self.opts.verify_ssl
            )
            if result == 200:
                print('%s uploaded successfully' % (self.opts.iso))


if __name__ == '__main__':
    vc = VCTools()
    sys.exit(vc.main())
