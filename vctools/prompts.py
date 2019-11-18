#!/usr/bin/env python
# vim: ts=4 sw=4 et
"""Prompts for User Inputs"""

import sys
import re
from pyVmomi import vim # pylint: disable=no-name-in-module
from vctools.query import Query
from vctools import Logger

class Prompts(Logger):
    """
    User prompts for selection configuration values.  It's best if these
    methods are configured as class methods
    """

    def __init__(self):
        pass

    @classmethod
    def fqdn(cls):
        """ Returns string name. """
        return input('FQDN: ')

    @classmethod
    def name(cls):
        """ Returns string name. """
        return input('Name: ')

    @classmethod
    def networks(cls, net_obj):
        """
        Method will prompt user to select a networks. Since multiple networks
        can be added to a VM, it will prompt the user to exit or add more.
        The networks should be selected in the order of which they want the
        interfaces set on the VM. For example, the first network selected will
        be configured on eth0 on the VM.

        Args:
            session (obj): Auth session object
            net_obj (cls): class has network managed object attribute
            multiple (bool): Allow for method to accept multiple inputs,
                otherwise it will return the first selection

        Returns:
            selected_networks (list): A list of selected networks
        """
        if getattr(net_obj, 'network'):
            networks = Query.list_obj_attrs(net_obj.network, 'name', view=False)
            networks.sort()
        else:
            raise ValueError('network managed object not found in %s' % (type(net_obj)))


        print('\n')
        print('%s Networks Found.\n' % (len(networks)))

        for num, opt in enumerate(networks, start=1):
            print('%s: %s' % (num, opt))

        selected_networks = []

        while True:
            if selected_networks:
                print('selected: ' + ','.join(selected_networks))

            val = input(
                '\nPlease select number:\n(Q)uit (S)how Networks\n'
                ).strip()

            # need to test whether selection is an integer or not.
            try:
                if int(val) <= len(networks):
                    # need to substract 1 since we start enumeration at 1.
                    val = int(val) - 1
                    selected_networks.append(networks[val])
                    continue
                else:
                    print('Invalid number.')
                    continue
            except ValueError:
                if val == 'Q':
                    break
                elif val == 'S':
                    for num, opt in enumerate(networks, start=1):
                        print('%s: %s' % (num, opt))
                else:
                    print('Invalid option.')
                    continue

        cls.logger.info(selected_networks)
        return selected_networks


    @classmethod
    def datastores(cls, session, cluster):
        """
        Method will prompt user to select a datastore from a cluster

        Args:
            session (obj): Auth session object
            cluster (str): Name of cluster

        Returns:
            datastore (str): Name of selected datastore
        """
        clusters = Query.create_container(
            session, session.content.rootFolder, [vim.ComputeResource], True
        )
        datastores = Query.return_datastores(clusters.view, cluster)

        print('\n')
        if (len(datastores) -1) == 0:
            print('No Datastores Found.')
            sys.exit(1)
        else:
            print('%s Datastores Found.\n' % (len(datastores) - 1))

        for num, opt in enumerate(datastores):
            # the first item is the header information, so we will
            # not allow it as an option.
            if num == 0:
                try:
                    print('\t%s' % ('{0:30}\t{1:10}\t{2:10}\t{3:6}\t{4:10}\t{5:6}'.format(*opt)))
                except TypeError:
                    pass
            else:
                try:
                    # pylint: disable=line-too-long
                    print(
                        '%s: %s' % (num, '{0:30}\t{1:10}\t{2:10}\t{3:6}\t{4:10}\t{5:6}'.format(*opt))
                    )
                except TypeError:
                    pass

        while True:
            val = int(input('\nPlease select number: ').strip())
            if val > 0 <= (len(datastores) - 1):
                break
            else:
                print('Invalid number')
                continue

        datastore = datastores[val][0]

        cls.logger.info(datastore)
        return datastore


    @classmethod
    def folders(cls, session, datacenter):
        """
        Method will prompt user to select a folder from a datacenter

        Args:
            session (obj):    Auth session object
            datacenter (str): Name of datacenter
        Returns:
            folder (str): Name of selected folder
        """
        datacenters = Query.create_container(
            session, session.content.rootFolder,
            [vim.Datacenter], True
        )
        folders = Query.list_vm_folders(
            datacenters.view, datacenter
        )
        folders.sort()

        for num, opt in enumerate(folders, start=1):
            print('%s: %s' % (num, opt))

        while True:
            val = int(input('\nPlease select number: ').strip())
            if int(val) <= len(folders):
                # need to substract 1 since we start enumeration at 1.
                val = int(val) - 1
                selected_folder = folders[val]
                break
            else:
                print('Invalid number.')
                continue

        cls.logger.info(selected_folder)

        if '->' in selected_folder:
            return selected_folder.split('->')[-1].strip()

        return selected_folder


    @classmethod
    def datacenters(cls, session):
        """
        Method will prompt user to select a datacenter

        Args:
            session (obj): Auth session object

        Returns:
            datacenter (str): Name of selected datacenter
        """
        datacenters_choices = Query.create_container(
            session, session.content.rootFolder,
            [vim.Datacenter], True
        )
        datacenters = Query.list_obj_attrs(datacenters_choices, 'name')
        datacenters.sort()

        for num, opt in enumerate(datacenters, start=1):
            print('%s: %s' % (num, opt))

        while True:
            val = int(input('\nPlease select number: ').strip())
            if int(val) <= len(datacenters):
                # need to substract 1 since we start enumeration at 1.
                val = int(val) - 1
                selected_datacenter = datacenters[val]
                break
            else:
                print('Invalid number.')
                continue


        cls.logger.info(selected_datacenter)
        return selected_datacenter


    @classmethod
    def clusters(cls, session):
        """
        Method will prompt user to select a cluster

        Args:
            session (obj): Auth session object

        Returns:
            cluster (str): Name of selected cluster
        """
        clusters_choices = Query.create_container(
            session, session.content.rootFolder,
            [vim.ComputeResource], True
        )
        clusters = Query.list_obj_attrs(clusters_choices, 'name')
        clusters.sort()

        for num, opt in enumerate(clusters, start=1):
            print('%s: %s' % (num, opt))

        while True:
            val = int(input('\nPlease select number: ').strip())
            if int(val) <= len(clusters):
                # need to substract 1 since we start enumeration at 1.
                val = int(val) - 1
                selected_cluster = clusters[val]
                break
            else:
                print('Invalid number.')
                continue

        cls.logger.info(selected_cluster)
        return selected_cluster


    @classmethod
    def guestids(cls):
        """
        Method will prompt user to select a guest ID (supported OS).
        """
        guestids = Query.list_guestids()
        for num, guestid in enumerate(guestids, start=1):
            print('%s:%s' % (num, guestid))

        while True:
            val = int(input('\nPlease select number: ').strip())
            if int(val) <= len(guestids):
                # need to substract 1 since we start enumeration at 1.
                val = int(val) - 1
                selected_guestid = guestids[val]
                break
            else:
                print('Invalid number.')
                continue


        cls.logger.info(selected_guestid)
        return selected_guestid

    @classmethod
    def ip_info(cls):
        """ Method will prompt for basic IP information """
        while True:
            ipaddr = input('\nPlease enter IP: ').strip()
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ipaddr):
                if ipaddr.split('.')[3] == '1':
                    print('IP ends in .1, which can potentially conflict with a gateway. Proceed?')
                    answer = input('\nConfirm yes or no: ').strip()
                    if 'no' in answer:
                        continue
                    elif 'yes' in answer:
                        break
                    else:
                        print('Invalid answer')
                        continue
                else:
                    break
            else:
                print('Invalid address')
                continue
        while True:
            netmask = input('\nPlease enter Netmask: ').strip()
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', netmask):
                break
            else:
                print('Invalid address')
                continue
        while True:
            gateway = input('\nPlease enter Gateway: ').strip()
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', gateway):
                break
            else:
                print('Invalid address')
                continue

        return (ipaddr, netmask, gateway)
