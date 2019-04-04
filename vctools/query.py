#!/usr/bin/env python
# vim: ts=4 sw=4 et
"""Query class for vctools.  All methods that obtain info should go here."""


from pyVmomi import vim # pylint: disable=no-name-in-module
from vctools import Logger

class Query(Logger):
    """
    Class handles queries for information regarding for vms, datastores
    and networks.
    """
    def __init__(self):
        pass

    @classmethod
    def disk_size_format(cls, num):
        """
        Method converts datastore size in bytes to human readable format.

        Args:
            num (int): Number
        """

        for attr in ['bytes', 'KB', 'MB', 'GB', 'TB']:
            if num < 1024.0:
                return '%3.2f %s' % (num, attr)
            num /= 1024.0
        return None


    @classmethod
    def create_container(cls, s_instance, *args):
        """
        Wrapper method for creating managed objects inside vim.view.ViewManager.

        Args:
            s_instance (obj): ServiceInstance
            args(list):
        """
        if hasattr(s_instance, 'content'):
            if hasattr(s_instance.content, 'viewManager'):
                return s_instance.content.viewManager.CreateContainerView(*args)

        return ValueError


    @classmethod
    def get_obj(cls, container, name):
        """
        Returns an object inside of ContainerView if it matches name.

        Args:
            container (obj):  Container object
            name (str):       Name of Container
        """

        for obj in container:
            if obj.name == name:
                return obj

        raise ValueError('%s not found.' % (name))

    @classmethod
    def list_obj_attrs(cls, container, attr, view=True):
        """
        Returns a list of attributes inside of container.

        Args:
            container (obj):  Container object
            attr (str):       Name of attribute within Container
            view (bool):      True appends view attribute to Container
        """
        if view:
            return [getattr(obj, attr) for obj in container.view]

        return [getattr(obj, attr) for obj in container]


    @classmethod
    def folders_lookup(cls, container, datacenter, name):
        """
        Returns the object for a folder name.  Currently, it only searches for
        the folder through one level of subfolders. This method is needed for
        building new virtual machines.

        Args:
            container (obj):  Container object
            datacenter (str): Name of datacenter
            name (str):       Name of folder
        """

        obj = Query.get_obj(container, datacenter)

        if hasattr(obj, 'vmFolder'):
            for folder in obj.vmFolder.childEntity:
                if hasattr(folder, 'childType'):
                    if folder.name == name:
                        return folder
                if hasattr(folder, 'childEntity'):
                    for item in folder.childEntity:
                        if hasattr(item, 'childType'):
                            if item.name == name:
                                return item
        return None

    @classmethod
    def list_vm_folders(cls, container, datacenter):
        """
        Returns a list of Virtual Machine folders.  Sub folders will be listed
        with its parent -> subfolder. Currently it only searches for one
        level of subfolders.

        Args:
            container (obj):  Container object
            datacenter (str): Name of datacenter
        """
        obj = Query.get_obj(container, datacenter)
        folders = []

        if hasattr(obj, 'vmFolder'):
            for folder in obj.vmFolder.childEntity:
                if hasattr(folder, 'childType'):
                    folders.append(folder.name)
                if hasattr(folder, 'childEntity'):
                    for item in folder.childEntity:
                        if hasattr(item, 'childType'):
                            folders.append(item.parent.name+' -> '+item.name)
        return folders


    @classmethod
    def datastore_most_space(cls, container, cluster):
        """
        Attempts to find the datastore with the most free space.

        Args:
            container (obj): Container object
            cluster (str):   Name of cluster

        """
        obj = Query.get_obj(container, cluster)
        datastores = {}

        if hasattr(obj, 'datastore'):
            for datastore in obj.datastore:
                # if datastore is a VMware File System
                if datastore.summary.type == 'VMFS':
                    free = int(datastore.summary.freeSpace)
                    datastores.update({datastore.name:free})


            most = max(datastores.values())
            for key, value in datastores.items():
                if value == most:
                    return key
        return None


    @classmethod
    def return_datastores(cls, container, cluster, header=True):
        """
        Returns a summary of disk space for datastores listed inside a
        cluster. Identical to list_datastore_info, but returns the datastores
        as an list object instead of printing them to stdout.

        Args:
            container (obj): Container object
            cluster (str):   Name of cluster
            header (bool):   Enables a header of info to datastore list.
        """

        obj = Query.get_obj(container, cluster)
        datastore_info = []


        if hasattr(obj, 'datastore'):
            for datastore in obj.datastore:
                info = []
                # type is long(bytes)
                free = int(datastore.summary.freeSpace)
                capacity = int(datastore.summary.capacity)

                # uncommitted is sometimes None, so we'll convert that to 0.
                if not datastore.summary.uncommitted:
                    uncommitted = int(0)
                else:
                    uncommitted = int(datastore.summary.uncommitted)

                provisioned = int((capacity - free) + uncommitted)

                provisioned_pct = '{0:.2%}'.format((provisioned / capacity))
                free_pct = '{0:.2%}'.format((free / capacity))

                info.append(datastore.name)
                info.append(Query.disk_size_format(capacity))
                info.append(Query.disk_size_format(provisioned))
                info.append(provisioned_pct)
                info.append(Query.disk_size_format(free))
                info.append(free_pct)

                datastore_info.append(info)

            # sort by datastore name
            datastore_info.sort(key=lambda x: x[0])

            if header:
                header = [
                    'Datastore', 'Capacity', 'Provisioned', 'Pct', 'Free Space', 'Pct'
                ]

                datastore_info.insert(0, header)

            return datastore_info
        return None


    @classmethod
    def return_anti_affinity_rules(cls, container, cluster):
        """
        Returns antiaffinity rules

        Args:
            container (obj): Container object
            cluster (str):   Name of cluster
        """

        cluster_obj = Query.get_obj(container, cluster)
        anti_affinity_rules = {}

        if hasattr(cluster_obj, 'configuration'):
            if hasattr(cluster_obj.configuration, 'rule'):
                for rule in cluster_obj.configuration.rule:

                    if isinstance(rule, vim.cluster.AntiAffinityRuleSpec):

                        aa_vms = []
                        if hasattr(rule, 'vm'):
                            for rule_vm in rule.vm:
                                aa_vms.append(rule_vm.name)
                        aa_rule = {rule.name : aa_vms}
                        anti_affinity_rules.update(aa_rule)

            return anti_affinity_rules
        return None


    @classmethod
    def list_vm_info(cls, container, datacenter):
        """
        Returns a list of names for VMs located inside a datacenter.

        """

        obj = Query.get_obj(container, datacenter)

        vms = {}

        # recurse through datacenter object attributes looking for vms.
        if hasattr(obj, 'vmFolder'):
            for virtmachine in obj.vmFolder.childEntity:
                if hasattr(virtmachine, 'childEntity'):
                    for virt in virtmachine.childEntity:
                        vms.update({virt.name:virt._moId})
                else:
                    vms.update({virtmachine.name:virt._moId})

        return vms


    @classmethod
    def get_vmid_by_name(cls, container, datacenter, name):
        """
        Returns the moId of matched name

        """

        obj = Query.get_obj(container, datacenter)

        # recurse through datacenter object attributes looking for vm that
        # matches hostname.
        if hasattr(obj, 'vmFolder'):
            for virtmachine in obj.vmFolder.childEntity:
                if hasattr(virtmachine, 'childEntity'):
                    for virt in virtmachine.childEntity:
                        if virt.name == name:
                            return virt._moId
                else:
                    if virt.name == name:
                        return virt._moId
        return None


    @classmethod
    def get_key(cls, obj, query):
        """
        Method will attempt to return the key associated with device so it can
        be used to edit existing devices. It will loop through all possible
        devices and return the key that matches query with the label attribute.

        Example:
            To get the key for the cdrom device, assuming obj is a
            VirtualMachine object

            get_key(virtual_machine, 'CD/DVD')

        Args:
            obj (obj): VirtualMachine object
            query (str): A string representation of the object attribute.

        Returns:
            keys (tuple): A tuple container the key and controllerKey associated
                with the device
        """

        if hasattr(obj, 'config'):
            for item in obj.config.hardware.device:
                if query in item.deviceInfo.label:
                    key = item.key
                    controller_key = item.controllerKey

        return (key, controller_key)


    @classmethod
    def get_label(cls, obj, query):
        """
        Method will attempt to return the label associated with the device key.
        It will loop through all possible devices and return the key that
        matches query with the label attribute.

        Example:
            To get the label for a device with key 1001, assuming obj is a
            VirtualMachine object

            get_label(virtual_machine, 1001)

        Args:
            obj (obj): VirtualMachine object
            query (int): A string representation of the object attribute.

        Returns:
            keys (str): The label associated with the key
        """

        if hasattr(obj, 'config'):
            for item in obj.config.hardware.device:
                if query == item.key:
                    label = item.deviceInfo.label

        return label

    @classmethod
    def list_guestids(cls):
        """
        Method will return an array of all supported guestids
        Returns:
            guestids (list): An ordered list of supported guestids
        """
        guestids = []
        for key in vim.vm.GuestOsDescriptor.GuestOsIdentifier.__dict__:
            # valid keys contain 'Guest' in name
            if 'Guest' in key:
                guestids.append(str(key))

        guestids.sort()

        return guestids


    @classmethod
    def vm_config(cls, container, name, createcfg=None):
        """
        Method will output the config for a Virtual Machine object.

        Args:
            name (str): The name of the VM.

        Returns:
            cfg (dict): The configs for the selected VM.
        """
        virtmachine = Query.get_obj(container, name)
        cfg = {}
        cfg['vmconfig'] = {}
        def vm_deep_query(data):
            """ deep query vmconfig """
            for key, val in data.__dict__.items():
                if hasattr(val, '__dict__'):
                    vm_deep_query(val)
                else:
                    if key in (
                            'memoryMB', 'numCPU', 'guestId', 'name', 'annotation',
                            'cpuHotAddEnabled', 'memoryHotAddEnabled'
                    ):
                        cfg['vmconfig'].update({key : val})

        vm_deep_query(virtmachine.config)

        # overriding key since numCPUs is how the value is assigned
        cfg['vmconfig']['numCPUs'] = cfg['vmconfig'].pop('numCPU')
        cfg['vmconfig']['nics'] = {}
        cfg['vmconfig']['disks'] = {}
        for item in virtmachine.config.hardware.device:
            if 'Hard disk' in item.deviceInfo.label:
                scsi = Query.get_label(virtmachine, item.controllerKey)
                if not scsi in cfg['vmconfig']['disks']:
                    cfg['vmconfig']['disks'].update({scsi : {}})
                if not item.capacityInBytes:
                    # try using the KiloBytes parameter if Bytes is None
                    capacity = item.capacityInKB / 1024 / 1024
                    cfg['vmconfig']['disks'][scsi].update({item.deviceInfo.label : int(capacity)})
                else:
                    capacity = item.capacityInBytes / 1024 / 1024 / 1024
                    cfg['vmconfig']['disks'][scsi].update({item.deviceInfo.label : int(capacity)})
            elif 'Network adapter' in item.deviceInfo.label:
                if 'DVSwitch' in item.deviceInfo.summary:
                    cfg['vmconfig']['switch_type'] = 'distributed'
                    for net in virtmachine.network:
                        if item.backing.port.portgroupKey == net.config.key:
                            cfg['vmconfig']['nics'].update({
                                item.deviceInfo.label : [
                                    item.macAddress, net.name
                                    ]
                                })
                else:
                    cfg['vmconfig']['nics'].update({
                        item.deviceInfo.label : [
                            item.macAddress, item.deviceInfo.summary
                            ]
                        })

        if createcfg:
            # make note of copy before overrides
            cfg['vmconfig'].update(
                {'annotation' : 'vctools cfg copy {0}'.format(cfg['vmconfig']['name'])}
            )

            cfg['vmconfig'].update({'name' : createcfg})

            cfg['vmconfig']['temp_disks'] = {}
            for scsi, disks in cfg['vmconfig']['disks'].items():
                cfg['vmconfig']['temp_disks'].update({int(scsi.split()[2]) : []})
                for dummy, val in disks.items():
                    cfg['vmconfig']['temp_disks'][int(scsi.split()[2])].append(val)

            cfg['vmconfig']['disks'] = cfg['vmconfig'].pop('temp_disks')

            # sort the nics correctly, and the last item in array is the network name
            cfg['vmconfig'].update(
                {'nics': [
                    value[-1] for (dummy, value) in sorted(cfg['vmconfig']['nics'].items())
                    ]
                }
            )

            return cfg

        return cfg

    @classmethod
    def vm_by_datastore(cls, container, cluster, datastore_name):
        """
        Method returns a list of VM names that are associated with cluster and datastore

        Args:
            container (obj): cluster container object
            cluster (str): Name of cluster to start the search
            datastore (str): Name of datastore to query

        Returns:
            vms (list): A sorted list of VM names.
        """
        obj = Query.get_obj(container, cluster)
        vms = []
        if hasattr(obj, 'datastore'):
            for datastore in obj.datastore:
                if datastore.name == datastore_name:
                    for virtual_machine in datastore.vm:
                        vms.append(virtual_machine.name)
        return sorted(vms)


    @classmethod
    def is_anti_affinity_rule(cls, cluster_obj, rule_name):
        """
        Method returns true if an AntiAffinity rule of the specified name exists
        in the specified cluster

        Args:
            cluster_obj (obj): cluster object for search
            rule_name (str): name of the AntiAffinity rule searched for

        Returns:
            True|False: true if rule exists, false if not
        """
        for existing_rule in cluster_obj.configuration.rule:
            if existing_rule.name == rule_name:
                return True
        return False


    @classmethod
    def is_vm_in_cluster(cls, cluster_obj, vm_obj):
        """
        Method returns true if the VM object listed exists in the stated cluster object,
        false otherwise.

        Args:
            cluster_obj (obj): cluster object for search
            vm_obj (obj): vm object searched for

        Returns:
            True|False: true if VM exists in cluster, false if not
        """
        match = False
        for clus_vm in cluster_obj.resourcePool.vm:
            if vm_obj == clus_vm:
                match = True

        return match
