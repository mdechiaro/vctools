#!/usr/bin/python
import sys
import yaml
import argparse
from pyVmomi import vim
from vctools.auth import Auth
from vctools.query import Query
from vctools.vmconfig import VMConfig

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



        # subparser
        subparsers = parser.add_subparsers(metavar='')


        # vcenter subparser
        vcenter_parser = subparsers.add_parser(
            'vcenter', help = 'vCenter URL'
        )
        vcenter_parser.set_defaults(cmd='vcenter')

        vcenter_parser.add_argument(
           'url', help = 'vCenter HTTPS URL'
        )


        # vcenter subparser subparsers
        vcenter_subparser = vcenter_parser.add_subparsers(metavar='')

        # query
        query_parser = vcenter_subparser.add_parser(
            'query', help = 'Query Info'
        )
        query_parser.set_defaults(cmd='query')

        query_parser.add_argument(
           'datastores',
            help = 'Returns information about Datastores.'
        )

        query_parser.add_argument(
           'vms',
            help = 'Returns information about Virtual Machines.'
        )

        query_parser.add_argument(
           'folders',
            help = 'Returns information about Folders.'
        )

        query_parser.add_argument(
           '--cluster',
            help = 'vCenter ComputeResource.'
        )
        


        # create
        create_parser = vcenter_subparser.add_parser(
            'create', help = 'Create Virtual Machines'
        )
        create_parser.set_defaults(cmd='create')

        create_parser.add_argument(
           'config', 
            help = 'YaML config for creating new Virtual Machines.'
        )

        # clone
        clone_parser = vcenter_subparser.add_parser(
            'clone', help = 'Clone Virtual Machines'
        )
        clone_parser.set_defaults(cmd='clone')

        # console
        console_parser = vcenter_subparser.add_parser(
            'console', help = 'Console Virtual Machines'
        )
        console_parser.set_defaults(cmd='console')


        # reconfig
        reconfig_parser = vcenter_subparser.add_parser(
            'reconfig', help = 'Reconfig Virtual Machines'
        )
        reconfig_parser.set_defaults(cmd='reconfig')

        # power
        power_parser = vcenter_subparser.add_parser(
            'power', help = 'Power Management for Virtual Machines'
        )
        power_parser.set_defaults(cmd='power')


        self.opts = parser.parse_args()
        self.help = parser.print_help


    def create_containers(self):
        self.clusters = query.create_container(
            auth.session, auth.session.content.rootFolder, 
            [vim.ComputeResource], True
        )

        self.folders = query.create_container(
            auth.session, auth.session.content.rootFolder, 
            [vim.Folder], True
        )



    def main(self):
        self.options()

        auth = vctools.auth.Auth(self.opts.vcenter.url)
        auth.login()

        query = vctools.query.Query()
        vmcfg = vctools.vmconfig.VMConfig()

        self.create_containers()


        if self.opts.vcenter.create:
            if self.opts.config:
                spec = yaml.load(open(config))
            else:
                print 'YaML config not found, exiting.'
                self.help
                sys.exit(1)

            cluster = query.get_obj(
                self.clusters.view, spec['vcenter']['cluster']
            )

            pool = cluster.resourcePool

            folder = query.get_obj(
                self.folders.view, spec['vcenter']['folder']
            )

            # convert kb to gb 
            gb = 1024*1024

            # counters for scsi controllers
            x = 0
            y = 0
            z = 0
            for scsi, disk in enumerate(spec['devices']['disks']):
                # setup the first four disks on a separate scsi controller
                while scsi <= 3:
                    devices.append(vmcfg.scsi_config(scsi))
                    devices.append(
                        vmcfg.disk_config(
                            cluster.datastore, datastore, disk*gb, unit = scsi
                        )
                    )

                # every remaining disk will be added sequentially across each
                # scsi controller.  
                if scsi == 4:
                    while scsi > 8:
                        while x < 4:
                            devices.append(
                                vmcfg.disk_config(
                                    cluster.datastore, datastore, disk*gb, 
                                    unit = x
                                )
                            )

                            x += 1

                        break

                if scsi == 8:
                    while scsi > 12:
                        while y < 4:
                            devices.append(
                                vmcfg.disk_config(
                                    cluster.datastore, datastore, disk*gb, 
                                    unit = y
                                )
                            )

                            y += 1

                        break

                if scsi == 12:
                    while scsi >= 16:
                        while z < 4:
                            devices.append(
                                vmcfg.disk_config(
                                    cluster.datastore, datastore, disk*gb, 
                                    unit = z
                                )
                            )

                            z += 1

                        break
                

            for nic in spec['devices']['nics']:
                devices.append(vmcfg.nic_config(cluster.network, nic))

            devices.append(vmcfg.cdrom_config())
           
            vmcfg.create(folder, pool, *devices, **spec['config'])


        if self.opts.vcenter.clone:
            pass

        if self.opts.vcenter.console:
            pass

        if self.opts.vcenter.reconfig:
            vmcfg.reconfig_vm(host, **reconfig)

        if self.opts.vcenter.query:

            if self.opts.vcenter.query.datastores:
                if self.opts.query.cluster:
                    cluster = self.opts.query.cluster
                    query.list_datastore_info(self.cluster.view, cluster)

        if self.opts.power:
            vmcfg.power(host, state)

if __name__ == '__main__':
    vc = VCTools()
    sys.exit(vc.main())
