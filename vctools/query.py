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


    def list_vm_names(self, container, datacenter):
        """
        Returns a list of names for VMs located inside a datacenter.

        """

        obj = self.get_obj(container, datacenter)

        vms = []

        # recurse through datacenter object attributes looking for vms.  
        if hasattr(obj, 'vmFolder'):
            for vm in obj.vmFolder.childEntity:
                if hasattr(vm, 'childEntity'):
                    for v in vm.childEntity:
                        vms.append(v.name)
                else:
                    vms.append(vm.name)    

        return vms

