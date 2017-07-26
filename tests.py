#!/usr/bin/python
""" Unit testing for vctools """
from __future__ import print_function
import socket
import unittest
import time
#
import requests
import yaml
#
from pyVmomi import vim # pylint: disable=no-name-in-module
from vctools.auth import Auth
from vctools.vmconfig import VMConfig
from vctools.query import Query

class Tests(unittest.TestCase):
    """ Class for various unit testing. """
    @classmethod
    def setUpClass(cls):
        """ Setup up Authentication """
        cfg = 'tests.yaml'
        cls.containers = None
        cls.config = yaml.load(open(cfg, 'r'))
        cls.vmcfg = VMConfig()
        cls.auth = Auth(cls.config['connect'].get('host', None))
        cls.auth.login(
            cls.config['connect'].get('user', None),
            cls.config['connect'].get('passwd', None),
            cls.config['connect'].get('domain', None),
        )

        cls.datacenters = Query.create_container(
            cls.auth.session, cls.auth.session.content.rootFolder,
            [vim.Datacenter], True
        )

        cls.clusters = Query.create_container(
            cls.auth.session, cls.auth.session.content.rootFolder,
            [vim.ComputeResource], True
        )

        cls.folders = Query.create_container(
            cls.auth.session, cls.auth.session.content.rootFolder,
            [vim.Folder], True
        )

        cls.virtual_machines = Query.create_container(
            cls.auth.session, cls.auth.session.content.rootFolder,
            [vim.VirtualMachine], True
        )

    @classmethod
    def tearDownClass(cls):
        """ Logout """
        cls.auth.logout()

    def test_authentication(self):
        """ Verify authenticated session """
        self.assertTrue(self.auth.session)

    def test_create_vm(self):
        """ Create a VM """
        if self.config.get('create', None):
            # for stdout and logging
            config_user_friendly = {}
            config_user_friendly.update(self.config['create'])

            datacenter = self.config['create']['vmconfig']['datacenter']
            cluster = self.config['create']['vmconfig']['cluster']
            datastore = self.config['create']['vmconfig']['datastore']
            folder = self.config['create']['vmconfig']['folder']

            cluster_obj = Query.get_obj(self.clusters.view, cluster)

            # list of scsi devices, max is 4.  Layout is a tuple containing the
            # key and configured device
            scsis = []
            # list of cdrom and disk devices
            devices = []

            # add the cdrom device
            devices.append(self.vmcfg.cdrom_config())

            # configure scsi controller and add disks to them.
            # to keep things simple, the max disks we allow in this example is
            # 4 (max scsi).
            for scsi, disk in enumerate(self.config['create']['vmconfig']['disks']):
                # setup the first four disks on a separate scsi controller
                # disk size is in GB
                scsis.append(self.vmcfg.scsi_config(scsi))
                devices.append(scsis[scsi][1])
                disk_cfg_opts = {}

                disk_cfg_opts.update(
                    {
                        'container' : cluster_obj.datastore,
                        'datastore' : datastore,
                        'size' : int(disk) * (1024*1024),
                        'controller' : scsis[scsi][0],
                        'unit' : 0,
                    }
                )
                devices.append(self.vmcfg.disk_config(**disk_cfg_opts))

            # configure each network and add to devices
            for nic in self.config['create']['vmconfig']['nics']:
                nic_cfg_opts = {}
                nic_cfg_opts.update({'container' : cluster_obj.network, 'network' : nic})
                devices.append(self.vmcfg.nic_config(**nic_cfg_opts))

            self.config['create']['vmconfig'].update({'deviceChange':devices})

            folder = Query.folders_lookup(
                self.datacenters.view, datacenter, folder
            )

            # delete keys that vSphere does not understand, so we can pass it a
            # dictionary to build the VM.
            del self.config['create']['vmconfig']['disks']
            del self.config['create']['vmconfig']['nics']
            del self.config['create']['vmconfig']['folder']
            del self.config['create']['vmconfig']['datastore']
            del self.config['create']['vmconfig']['datacenter']
            del self.config['create']['vmconfig']['cluster']

            pool = cluster_obj.resourcePool
            self.assertTrue(
                self.vmcfg.create(folder, datastore, pool, **self.config['create']['vmconfig'])
            )
            time.sleep(2)
        else:
            self.skipTest('create options not found, skipping test.')

    def test_mkbootiso(self):
        """ mkbootiso test """
        if self.config.get('mkbootiso', None):
            mkbootiso_url = 'https://{0}/api/mkbootiso'.format(socket.getfqdn())
            headers = {'Content-Type' : 'application/json'}
            response = requests.post(
                mkbootiso_url, json=self.config['mkbootiso'], headers=headers, verify=False
            )
            self.assertEqual(200, response.status_code)
        else:
            self.skipTest('mkbootiso options not found, skipping test.')

    def test_upload_iso(self):
        """ upload iso test """
        if self.config.get('upload', None):
            upload_iso_args = {
                'host': self.config['connect'].get('host', None),
                'datacenter' : self.config['upload'].get('datacenter', None),
                'datastore' : self.config['upload'].get('datastore', None),
                'dest_folder' : self.config['upload'].get('dest_folder', None),
                'cookie' : self.auth.session._stub.cookie,
                'iso' : self.config['upload'].get('iso', None),
            }
            result = self.vmcfg.upload_iso(**upload_iso_args)
            # match 200 or 201
            print(
                'Upload ISO {0} to {1}'.format(
                    upload_iso_args['iso'],
                    upload_iso_args['datastore'] +
                    ' ' + upload_iso_args['dest_folder']
                    )
            )
            self.assertRegexpMatches(str(result), r'20[0-1]')
        else:
            self.skipTest('upload options not found, skipping test.')

    def test_mount_iso(self):
        """ mount an iso test """
        if self.config.get('mount', None):
            datastore = self.config['mount']['datastore']
            path = self.config['mount']['path']
            name = self.config['mount']['name']

            host = Query.get_obj(
                self.virtual_machines.view, name
            )

            cdrom_cfg = []

            key, controller = Query.get_key(host, 'CD/DVD')

            if not path.endswith('.iso'):
                if path.endswith('/'):
                    path = path + name + '.iso'
                else:
                    path = path +'/'+ name + '.iso'

            # path is relative (strip first character)
            if path.startswith('/'):
                path = path.lstrip('/')

            cdrom_cfg_opts = {}
            cdrom_cfg_opts.update(
                {
                    'datastore' : datastore,
                    'iso_path' : path,
                    'iso_name' : name,
                    'key': key,
                    'controller' : controller,
                }
            )
            cdrom_cfg.append(self.vmcfg.cdrom_config(**cdrom_cfg_opts))

            config = {'deviceChange' : cdrom_cfg}
            print('Mount ISO {0} on {1}'.format(path, name))
            self.assertTrue(self.vmcfg.reconfig(host, **config))
        else:
            self.skipTest('mount options not found, skipping test.')

    def test_umount_iso(self):
        """ umount an iso test """
        if self.config.get('umount', None):
            name = self.config['mount']['name']
            host = Query.get_obj(self.virtual_machines.view, name)

            key, controller = Query.get_key(host, 'CD/DVD')

            cdrom_cfg = []
            cdrom_cfg_opts = {}
            cdrom_cfg_opts.update(
                {
                    'umount' : True,
                    'key' : key,
                    'controller' : controller,
                }
            )
            cdrom_cfg.append(self.vmcfg.cdrom_config(**cdrom_cfg_opts))
            config = {'deviceChange' : cdrom_cfg}
            print('Umount ISO on {0}'.format(name))
            self.assertTrue(self.vmcfg.reconfig(host, **config))
        else:
            self.skipTest('umount options not found, skipping test.')

    def test_power_vm(self):
        """ power test """
        if self.config.get('power', None):
            name = self.config['power']['name']
            state = self.config['power']['state']
            host = Query.get_obj(self.virtual_machines.view, name)
            print('Adjust power state to "{0}" on {1}'.format(state, name))
            self.vmcfg.power(host, state)
        else:
            self.skipTest('power options not found, skipping test.')

if __name__ == "__main__":
    unittest.main(verbosity=2)
