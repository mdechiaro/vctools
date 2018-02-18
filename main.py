#!/usr/bin/python
# vim: ts=4 sw=4 et
"""
vctools is a Python module using pyVmomi which aims to simplify command-line
operations inside VMWare vCenter.

https://github.com/mdechiaro/vctools/
"""
from __future__ import print_function
import logging
from getpass import getuser
import sys
import yaml
#
from pyVmomi import vim # pylint: disable=no-name-in-module
from vctools.argparser import ArgParser
from vctools.auth import Auth
from vctools.vmconfig_helper import VMConfigHelper
from vctools.query import Query
from vctools.prompts import Prompts
from vctools.cfgchecker import CfgCheck
from vctools import Logger

class VCTools(Logger):
    """
    Main VCTools class.
    """

    def __init__(self, opts):
        self.opts = opts
        self.auth = None
        self.clusters = None
        self.datacenters = None
        self.folders = None
        self.query = None
        self.virtual_machines = None
        self.vmcfg = None

    def create_containers(self):
        """
        Sets up different containers, or views, inside vSphere.

        These containers can then be queried to obtain different information
        about an object.
            vim.Datacenter
            vim.ComputeResource
            vim.Folder
            vim.VirtualMachine
        """


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


    def main(self):
        """
        This is the main method, which parses all the argparse options and runs
        the necessary code blocks if True.
        """

        try:
            self.logger.debug(self.opts)

            self.auth = Auth(self.opts.host)
            self.auth.login(
                self.opts.user, self.opts.passwd, self.opts.domain, self.opts.passwd_file
            )
            self.query = Query()
            self.create_containers()
            self.vmcfg = VMConfigHelper(self.auth, self.opts, argparser.dotrc)
            if self.opts.cmd == 'create':
                if self.opts.config:
                    for cfg in self.opts.config:
                        spec = self.vmcfg.dict_merge(argparser.dotrc, yaml.load(cfg))
                        cfgcheck_update = CfgCheck.cfg_checker(spec, self.auth, self.opts)
                        spec['vmconfig'].update(
                            self.vmcfg.dict_merge(spec['vmconfig'], cfgcheck_update)
                        )
                        spec = self.vmcfg.pre_create_hooks(**spec)
                        spec = self.vmcfg.create_wrapper(**spec)
                        self.vmcfg.post_create_hooks(**spec)
                        filename = spec['vmconfig']['name'] + '.yaml'
                        server_cfg = {}
                        server_cfg['vmconfig'] = {}
                        server_cfg['vmconfig'].update(spec['vmconfig'])
                        if spec.get('mkbootiso', None):
                            server_cfg['mkbootiso'] = {}
                            server_cfg['mkbootiso'].update(spec['mkbootiso'])

                        # yaml cannot parse this format
                        del server_cfg['vmconfig']['deviceChange']

                        print(
                            yaml.dump(server_cfg, default_flow_style=False),
                            file=open(filename, 'w')
                        )

            if self.opts.cmd == 'mount':
                self.vmcfg.mount_wrapper(self.opts.datastore, self.opts.path, *self.opts.name)

            if self.opts.cmd == 'power':
                self.vmcfg.power_wrapper(self.opts.power, *self.opts.name)

            if self.opts.cmd == 'umount':
                self.vmcfg.umount_wrapper(*self.opts.name)

            if self.opts.cmd == 'upload':
                self.vmcfg.upload_wrapper(
                    self.opts.datastore, self.opts.dest,
                    self.opts.verify_ssl, *self.opts.iso
                )

            if self.opts.cmd == 'add':
                devices = []
                hostname = self.query.get_obj(self.virtual_machines.view, self.opts.name)

                # nics
                if self.opts.device == 'nic':
                    # Prompt if network is not declared
                    if not self.opts.network:
                        # only first selection allowed for now
                        network = Prompts.networks(hostname.summary.runtime.host)[0]
                    else:
                        network = self.opts.network
                    nic_cfg_opts = {}
                    esx_host_net = hostname.summary.runtime.host.network
                    nic_cfg_opts.update({'container' : esx_host_net, 'network' : network})
                    if self.opts.driver == 'e1000':
                        nic_cfg_opts.update({'driver': 'VirtualE1000'})
                    devices.append(self.vmcfg.nic_config(**nic_cfg_opts))
                    if devices:
                        self.logger.info(
                            'add hardware %s network: %s', hostname.name, network
                        )
                        self.vmcfg.reconfig(hostname, **{'deviceChange': devices})

            if self.opts.cmd == 'reconfig':
                host = Query.get_obj(self.virtual_machines.view, self.opts.name)
                if self.opts.cfgs:
                    self.logger.info(
                        'reconfig: %s cfgs: %s', host.name,
                        ' '.join('%s=%s' % (k, v) for k, v in self.opts.cfgs.iteritems())
                    )
                    self.vmcfg.reconfig(host, **self.opts.cfgs)
                if self.opts.folder:
                    self.vmcfg.folder_recfg()
                if self.opts.device == 'disk':
                    self.vmcfg.disk_recfg()
                if self.opts.device == 'nic':
                    self.vmcfg.nic_recfg()

            if self.opts.cmd == 'query':
                if self.opts.datastores:
                    if self.opts.cluster:
                        datastores = self.query.return_datastores(
                            self.clusters.view, self.opts.cluster
                        )

                        for row in datastores:
                            print('{0:30}\t{1:10}\t{2:10}\t{3:6}\t{4:10}\t{5:6}'.format(*row))
                    else:
                        print('--cluster <name> required with --datastores flag')
                if self.opts.folders:
                    if self.opts.datacenter:
                        folders = self.query.list_vm_folders(
                            self.datacenters.view, self.opts.datacenter
                        )
                        folders.sort()
                        for folder in folders:
                            print(folder)
                    else:
                        print('--datacenter <name> required with --folders flag')
                if self.opts.clusters:
                    clusters = self.query.list_obj_attrs(self.clusters, 'name')
                    clusters.sort()
                    for cluster in clusters:
                        print(cluster)
                if self.opts.networks:
                    if self.opts.cluster:
                        cluster = self.query.get_obj(self.clusters.view, self.opts.cluster)
                        networks = self.query.list_obj_attrs(cluster.network, 'name', view=False)
                        networks.sort()
                        for net in networks:
                            print(net)
                    else:
                        print('--cluster <name> required with --networks flag')
                if self.opts.vms:
                    vms = self.query.list_vm_info(self.datacenters.view, self.opts.datacenter)
                    for key, value in vms.iteritems():
                        print(key, value)
                if self.opts.vmconfig:
                    for name in self.opts.vmconfig:
                        if self.opts.createcfg:
                            print(
                                yaml.dump(
                                    self.query.vm_config(
                                        self.virtual_machines.view, name, self.opts.createcfg
                                    ),
                                    default_flow_style=False
                                )
                            )
                        else:
                            print(
                                yaml.dump(
                                    self.query.vm_config(self.virtual_machines.view, name),
                                    default_flow_style=False
                                )
                            )

            self.auth.logout()

        except ValueError as err:
            self.logger.error(err, exc_info=False)
            self.auth.logout()
            sys.exit(3)

        except vim.fault.InvalidLogin as loginerr:
            self.logger.error(loginerr.msg, exc_info=False)
            sys.exit(2)

        except KeyboardInterrupt as err:
            self.logger.error(err, exc_info=False)
            self.auth.logout()
            sys.exit(1)


if __name__ == '__main__':
    # setup argument parsing
    argparser = ArgParser()
    argparser.setup_args(**argparser.dotrc)
    options = argparser.sanitize(argparser.parser.parse_args())

    # setup logging
    log_level = options.level.upper()
    log_file = options.logfile
    log_format = '%(asctime)s %(username)s %(levelname)s %(module)s %(funcName)s %(message)s'
    logging.basicConfig(
        filename=log_file, level=getattr(logging, log_level), format=log_format
    )

    # set up logging to console for error messages
    console = logging.StreamHandler()
    console.setLevel(logging.ERROR)
    logging.getLogger().addHandler(console)

    # force username on logs and apply to all handlers
    class AddFilter(logging.Filter):
        """ Add filter class for adding attributes to logs """
        def filter(self, record):
            record.username = getuser()
            return True

    for handler in logging.root.handlers:
        handler.addFilter(AddFilter())

    vctools = VCTools(options)
    sys.exit(vctools.main())
