#!/usr/bin/python
from __future__ import division
from __future__ import print_function
#
from pyVmomi import vim # pylint: disable=E0611
#

class Query(object):
    def __init__(self):
        """
        Class handles queries for information regarding for vms, datastores
        and networks.
        """
        pass


    @classmethod
    def disk_size_format(cls, num):
        """Method converts datastore size in bytes to human readable format."""

        for attr in ['bytes', 'KB', 'MB', 'GB', 'TB']:
            if num < 1024.0:
                return '%3.2f %s' % (num, attr)
            num /= 1024.0


    def create_container(self, si, *args):
        """
        Wrapper method for creating managed objects inside vim.view.ViewManager.

        """
        if hasattr(si, 'content'):
            if hasattr(si.content, 'viewManager'):
                return si.content.viewManager.CreateContainerView(*args)
            else:
                raise Exception
        else:
            raise Exception


    def get_obj(self, container, name):
        """
        Returns an object inside of ContainerView if it matches name.

        """

        for obj in container:
            if obj.name == name:
                return obj


    def list_obj_attrs(self, container, attr, view = True):
        """
        Returns a list of attributes inside of container.

        """
        if view:
            return [getattr(obj, attr) for obj in container.view]
        else:
            return [getattr(obj, attr) for obj in container]


    def folders_lookup(self, container, datacenter, name):
        """
        Returns the object for a folder name.  Currently, it only searches for
        the folder through one level of subfolders. This method is needed for
        building new virtual machines.

        """
        obj = self.get_obj(container, datacenter)
        folders = []

        if hasattr(obj, 'vmFolder'):
            for folder in obj.vmFolder.childEntity:
                if hasattr(folder, 'childType'):
                    if folder.name == name:
                        return folder
                if hasattr(folder, 'childEntity'):
                    for f in folder.childEntity:
                        if hasattr(f, 'childType'):
                            if f.name == name:
                                return f

    def list_vm_folders(self, container, datacenter):
        """
        Returns a list of Virtual Machine folders.  Sub folders will be listed
        with its parent -> subfolder. Currently it only searches for one
        level of sub folders.

        container
        """
        obj = self.get_obj(container, datacenter)
        folders = []

        if hasattr(obj, 'vmFolder'):
            for folder in obj.vmFolder.childEntity:
                if hasattr(folder, 'childType'):
                    folders.append(folder.name)
                if hasattr(folder, 'childEntity'):
                    for f in folder.childEntity:
                        if hasattr(f, 'childType'):
                            folders.append(f.parent.name + ' -> ' + f.name)
        return folders



    def list_datastore_info(self, container, datacenter, filter = None):
        """
        Returns a summary of disk space for datastores listed inside a
        datacenter.

        """

        obj = self.get_obj(container, datacenter)

        datastore_info = []
        header = [
            'Datastore', 'Capacity', 'Provisioned', 'Pct', 'Free Space', 'Pct'
        ]
        datastore_info.append(header)

        if filter:
            for datastore in obj.datastore:
                if filter in datastore.name:
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
                    info.append(self.disk_size_format(capacity))
                    info.append(self.disk_size_format(provisioned))
                    info.append(provisioned_pct)
                    info.append(self.disk_size_format(free))
                    info.append(free_pct)

                    datastore_info.append(info)
        else:
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
                info.append(self.disk_size_format(capacity))
                info.append(self.disk_size_format(provisioned))
                info.append(provisioned_pct)
                info.append(self.disk_size_format(free))
                info.append(free_pct)

                datastore_info.append(info)


        for row in datastore_info:
            print ('{0:30}\t{1:10}\t{2:10}\t{3:6}\t{4:10}\t{5:6}'.format(*row))


    def list_vm_info(self, container, datacenter):
        """
        Returns a list of names for VMs located inside a datacenter.

        """

        obj = self.get_obj(container, datacenter)

        vms = {}

        # recurse through datacenter object attributes looking for vms.
        if hasattr(obj, 'vmFolder'):
            for vm in obj.vmFolder.childEntity:
                if hasattr(vm, 'childEntity'):
                    for v in vm.childEntity:
                        vms.update({v.name:v._moId})
                else:
                    vms.update({vm.name:v._moId})

        return vms

    def get_vmid_by_name(self, container, datacenter, name):
        """
        Returns the moId of matched name

        """

        obj = self.get_obj(container, datacenter)

        vms = {}

        # recurse through datacenter object attributes looking for vm that
        # matches hostname.
        if hasattr(obj, 'vmFolder'):
            for vm in obj.vmFolder.childEntity:
                if hasattr(vm, 'childEntity'):
                    for v in vm.childEntity:
                        if v.name == name:
                            return v._moId
                else:
                    if v.name == name:
                        return v._moId

