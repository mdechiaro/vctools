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
from vctools.prompts import Prompts
from vctools.query import Query
from vctools.cfgchecker import CfgCheck
from vctools import Logger

class VCTools(Logger):
    """
    Main VCTools class.
    """

    def __init__(self, opts):
        self.opts = opts
        self.auth = None
        self.vmcfg = None
        self.call_count = None

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


            virtual_machines_container = Query.create_container(
                self.auth.session, self.auth.session.content.rootFolder,
                [vim.VirtualMachine], True
            )

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
                hostname = Query.get_obj(virtual_machines_container.view, self.opts.name)

                # nics
                if self.opts.device == 'nic':
                    self.vmcfg.add_nic_recfg(hostname)

            if self.opts.cmd == 'reconfig':
                host = Query.get_obj(virtual_machines_container.view, self.opts.name)
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
                datacenters_container = Query.create_container(
                    self.auth.session, self.auth.session.content.rootFolder,
                    [vim.Datacenter], True
                )
                clusters_container = Query.create_container(
                    self.auth.session, self.auth.session.content.rootFolder,
                    [vim.ComputeResource], True
                )
                if self.opts.datastores:
                    if self.opts.cluster:
                        datastores = Query.return_datastores(
                            clusters_container.view, self.opts.cluster
                        )
                        for row in datastores:
                            print('{0:30}\t{1:10}\t{2:10}\t{3:6}\t{4:10}\t{5:6}'.format(*row))
                    else:
                        cluster = Prompts.clusters(self.auth.session)
                        datastores = Query.return_datastores(clusters_container.view, cluster)
                        for row in datastores:
                            print('{0:30}\t{1:10}\t{2:10}\t{3:6}\t{4:10}\t{5:6}'.format(*row))
                if self.opts.folders:
                    if self.opts.datacenter:
                        folders = Query.list_vm_folders(
                            datacenters_container.view, self.opts.datacenter
                        )
                        folders.sort()
                        for folder in folders:
                            print(folder)
                    else:
                        datacenter = Prompts.datacenters(self.auth.session)
                        folders = Query.list_vm_folders(datacenters_container.view, datacenter)
                        folders.sort()
                        for folder in folders:
                            print(folder)
                if self.opts.clusters:
                    clusters = Query.list_obj_attrs(clusters_container, 'name')
                    clusters.sort()
                    for cluster in clusters:
                        print(cluster)
                if self.opts.networks:
                    if self.opts.cluster:
                        cluster = Query.get_obj(clusters_container.view, self.opts.cluster)
                        networks = Query.list_obj_attrs(cluster.network, 'name', view=False)
                        networks.sort()
                        for net in networks:
                            print(net)
                    else:
                        cluster_name = Prompts.clusters(self.auth.session)
                        cluster = Query.get_obj(clusters_container.view, cluster_name)
                        networks = Query.list_obj_attrs(cluster.network, 'name', view=False)
                        networks.sort()
                        for net in networks:
                            print(net)
                if self.opts.vms:
                    vms = Query.list_vm_info(datacenters_container.view, self.opts.datacenter)
                    for key, value in vms.iteritems():
                        print(key, value)
                if self.opts.vmconfig:
                    for name in self.opts.vmconfig:
                        if self.opts.createcfg:
                            print(
                                yaml.dump(
                                    Query.vm_config(
                                        virtual_machines_container.view, name, self.opts.createcfg
                                    ),
                                    default_flow_style=False
                                )
                            )
                        else:
                            print(
                                yaml.dump(
                                    Query.vm_config(virtual_machines_container.view, name),
                                    default_flow_style=False
                                )
                            )
                if self.opts.vm_by_datastore:
                    if self.opts.cluster and self.opts.datastore:
                        vms = Query.vm_by_datastore(
                            clusters_container.view, self.opts.cluster, self.opts.datastore
                        )
                        for vm_name in vms:
                            print(vm_name)
                    else:
                        if not self.opts.cluster:
                            cluster = Prompts.clusters(self.auth.session)
                        if not self.opts.datastore:
                            datastore = Prompts.datastores(self.auth.session, cluster)
                        print()

                        vms = Query.vm_by_datastore(clusters_container.view, cluster, datastore)
                        for vm_name in vms:
                            print(vm_name)

            self.call_count = self.auth.session.content.sessionManager.currentSession.callCount
            self.auth.logout()
            self.logger.debug('Call count: {0}'.format(self.call_count))

        except ValueError as err:
            self.logger.error(err, exc_info=False)
            self.auth.logout()
            self.logger.debug('Call count: {0}'.format(self.call_count))
            sys.exit(3)

        except vim.fault.InvalidLogin as loginerr:
            self.logger.error(loginerr.msg, exc_info=False)
            sys.exit(2)

        except KeyboardInterrupt as err:
            self.logger.error(err, exc_info=False)
            self.auth.logout()
            self.logger.debug('Call count: {0}'.format(self.call_count))
            sys.exit(1)


if __name__ == '__main__':
    argparser = ArgParser()
    argparser.setup_args(**argparser.dotrc)
    options = argparser.sanitize(argparser.parser.parse_args())

    log_level = options.level.upper()
    log_file = options.logfile
    log_format = '%(asctime)s %(username)s %(levelname)s %(module)s %(funcName)s %(message)s'

    logging.basicConfig(
        filename=log_file, level=getattr(logging, log_level), format=log_format
    )

    console_log_level = options.console_level.upper()
    console = logging.StreamHandler(stream=getattr(sys, options.console_stream))
    console.setLevel(getattr(logging, console_log_level))

    logging.getLogger().addHandler(console)

    class AddFilter(logging.Filter):
        """
        Class adds attributes to logging that can be added to the logging format
        """
        def filter(self, record):
            # force username on logs
            record.username = getuser()
            return True

    for handler in logging.root.handlers:
        handler.addFilter(AddFilter())

    vct = VCTools(options)
    sys.exit(vct.main())
