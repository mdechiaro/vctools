#!/usr/bin/python
""" Checks the user config and prompts for more info"""
from __future__ import print_function
from pyVmomi import vim # pylint: disable=E0611
from vctools.prompts import Prompts
from vctools.query import Query

class CfgCheck(object):
    """ Cfg checker class."""
    def __init__(self):
        pass

    @staticmethod
    def cfg_checker(cfg, auth, opts):
        """
        Checks config for a valid configuration, and prompts user if
        information is missing

        Args:
            cfg    (obj): Yaml object
        """
        clusters = Query.create_container(
            auth.session, auth.session.content.rootFolder,
            [vim.ComputeResource], True
        )
        # name
        if 'vmconfig' in cfg:

            # name
            if 'name' in cfg['vmconfig']:
                name = cfg['vmconfig']['name']
            else:
                name = Prompts.name()
            # guestid
            if 'guestId' in cfg['vmconfig']:
                guestid = cfg['vmconfig']['guestId']
            else:
                guestid = Prompts.guestids()
                print('\n%s selected.' % (guestid))
            # cluster
            if 'cluster' in cfg['vmconfig']:
                cluster = cfg['vmconfig']['cluster']
                cluster_obj = Query.get_obj(clusters.view, cluster)
            else:
                cluster = Prompts.clusters(auth.session)
                cluster_obj = Query.get_obj(clusters.view, cluster)
                print('\n%s selected.' % (cluster))
            # datastore
            if 'datastore' in cfg['vmconfig']:
                datastore = cfg['vmconfig']['datastore']
            else:
                datastore = Prompts.datastores(auth.session, cluster)
                print('\n%s selected.' % (datastore))
            # datacenter
            if not opts.datacenter:
                datacenter = Prompts.datacenters(auth.session)
                print('\n%s selected.' % (datacenter))
            else:
                datacenter = opts.datacenter
            # nics
            if 'nics' in cfg['vmconfig']:
                nics = cfg['vmconfig']['nics']
                print('nics: %s' % (nics))
            else:
                nics = Prompts.networks(cluster_obj)
                print('\n%s selected.' % (','.join(nics)))
            # folder
            if 'folder' in cfg['vmconfig']:
                folder = cfg['vmconfig']['folder']
            else:
                folder = Prompts.folders(auth.session, datacenter)
                print('\n%s selected.' % (folder))
        else:
            name = Prompts.name()
            guestid = Prompts.guestids()
            print('\n%s selected.' % (guestid))
            cluster = Prompts.clusters(auth.session)
            print('\n%s selected.' % (cluster))
            datastore = Prompts.datastores(auth.session, cluster)
            print('\n%s selected.' % (datastore))
            datacenter = Prompts.datacenters(auth.session)
            print('\n%s selected.' % (datacenter))
            nics = Prompts.networks(cluster_obj)
            print('\n%s selected.' % (','.join(nics)))
            folder = Prompts.folders(auth.session, datacenter)
            print('\n%s selected.' % (folder))

        output = {
            'name': name,
            'guestId': guestid,
            'cluster': cluster,
            'datastore': datastore,
            'nics': nics,
            'folder': folder
        }

        return output
