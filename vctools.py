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


        # vc subparser
        vc_parser = subparsers.add_parser(
            'vc', help = 'vCenter URL'
        )
        vc_parser.set_defaults(cmd='url')

        vc_parser.add_argument(
           'url', help = 'vCenter HTTPS URL'
        )


        # vc subparser subparsers
        vc_subparser = vc_parser.add_subparsers(metavar='')

        # query
        query_parser = vc_subparser.add_parser(
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
        create_parser = vc_subparser.add_parser(
            'create',
            help = 'Create Virtual Machines'
        )
        create_parser.set_defaults(cmd='config')

        create_parser.add_argument(
           'config', type=file,
            help = 'YaML config for creating new Virtual Machines.'
        )

        # clone
        clone_parser = vc_subparser.add_parser(
            'clone', help = 'Clone Virtual Machines'
        )
        clone_parser.set_defaults(cmd='clone')

        # console
        console_parser = vc_subparser.add_parser(
            'console', help = 'Console Virtual Machines'
        )
        console_parser.set_defaults(cmd='console')


        # reconfig
        reconfig_parser = vc_subparser.add_parser(
            'reconfig', help = 'Reconfig Virtual Machines'
        )
        reconfig_parser.set_defaults(cmd='reconfig')

        # power
        power_parser = vc_subparser.add_parser(
            'power', help = 'Power Management for Virtual Machines'
        )
        power_parser.set_defaults(cmd='power')


        self.opts = parser.parse_args()
        self.help = parser.print_help


    def create_containers(self):
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

        self.auth = Auth(self.opts.url)
        self.auth.login()

        self.query = Query()
        vmcfg = VMConfig()

        self.create_containers()


        #if self.opts.create:
        if self.opts.config:
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

            # counters for scsi controllers
            x = 0
            y = 0
            z = 0
            for scsi, disk in enumerate(spec['devices']['disks']):
                # setup the first four disks on a separate scsi controller
                self.devices.append(vmcfg.scsi_config(scsi))
                self.devices.append(
                    vmcfg.disk_config(
                        cluster.datastore, datastore, disk*gb, unit = scsi
                    )
                )

                # every remaining disk will be added sequentially across each
                # scsi controller.  
                #if scsi == 4:
                #    print 'building second four disks.'
                #    while scsi > 8:
                #        while x < 4:
                #            self.devices.append(
                #                vmcfg.disk_config(
                #                    cluster.datastore, datastore, disk*gb, 
                #                    unit = x
                #                )
                #            )

                #            x += 1

                #        break
                #        scsi += 1

                #if scsi == 8:
                #    print 'building third four disks.'
                #    while scsi > 12:
                #        while y < 4:
                #            self.devices.append(
                #                vmcfg.disk_config(
                #                    cluster.datastore, datastore, disk*gb, 
                #                    unit = y
                #                )
                #            )

                #            y += 1

                #        break

                #if scsi == 12:
                #    print 'building fourth four disks.'
                #    while scsi >= 16:
                #        while z < 4:
                #            self.devices.append(
                #                vmcfg.disk_config(
                #                    cluster.datastore, datastore, disk*gb, 
                #                    unit = z
                #                )
                #            )

                #            z += 1

                #        break
                

            for nic in spec['devices']['nics']:
                self.devices.append(vmcfg.nic_config(cluster.network, nic))

            self.devices.append(vmcfg.cdrom_config())
           
            vmcfg.create(folder, pool, *self.devices, **spec['config'])


if __name__ == '__main__':
    vc = VCTools()
    sys.exit(vc.main())
