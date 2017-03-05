#!/usr/bin/python
# vim: ts=4 sw=4 et
"""Various config options for Virtual Machines."""
from __future__ import print_function
import textwrap
import sys
from random import uniform
import requests
from pyVmomi import vim # pylint: disable=E0611
from vctools.query import Query
from vctools import Logger

class VMConfig(Query, Logger):
    """
    Class simplifies VM builds outside of using the client or Web App.
    Class can handle setting up a complete VM with multiple devices attached.
    It can also handle the addition of mutiple disks attached to multiple SCSI
    controllers, as well as multiple network interfaces.
    """

    def __init__(self):
        """ Define our class attributes here. """
        Query.__init__(self)
        self.scsi_key = None


    @classmethod
    def question_and_answer(cls, host, **answered):
        """
        Method handles the questions and answers provided by the program.

        Args:
            host (obj): VirtualMachine object
            answered (dict): A key value pair of already answered questions.
        """

        if host.runtime.question:
            qid = host.runtime.question.id

            if not qid in answered.keys():
                print('\n')
                print('\n'.join(textwrap.wrap(host.runtime.question.text, 80)))
                choices = {}
                for option in host.runtime.question.choice.choiceInfo:
                    choices.update({option.key : option.label})
                    sys.stdout.write('\t%s: %s' % (option.key, option.label))

                warn = textwrap.dedent("""\
                    Warning: The VM may be in a suspended
                    state until this question is answered.""").strip()

                print(textwrap.fill(warn, width=80))

                while True:
                    answer = raw_input('\nPlease select number: ').strip()

                    # check if answer is an appropriate number
                    if int(answer) <= len(choices.keys()) - 1:
                        break
                    else:
                        continue

                if answer:
                    host.AnswerVM(qid, str(answer))
                    answered.update({qid:answer})
                    return answered


    def upload_iso(self, **kwargs):
        """
        Method uploads iso to dest_folder.

        Kwargs:
            host (str):        vCenter host
            cookie (attr):     Session Class Cookie (auth.session._stub.cookie)
            datacenter (str):  Name of Datacenter that has access to datastore.
            dest_folder (str): Folder that will store the iso.
            datastore (str):   Datastore that will store the iso.
            iso (str):         Absolute path of ISO file
            verify (bool):     Enable or disable SSL certificate validation.
        """
        host = kwargs.get('host', None)
        cookie = kwargs.get('cookie', None)
        datacenter = kwargs.get('datacenter', None)
        dest_folder = kwargs.get('dest_folder', None)
        datastore = kwargs.get('datastore', None)
        iso = kwargs.get('iso', None)
        verify = kwargs.get('verify', False)

        # we need the absolute path to open the binary locally, but only the
        # filename for uploading to the datastore.
        if '/' in iso:
            # the last item in the list will be the filename
            iso_name = iso.split('/')[-1]
        else:
            iso_name = iso

        if not dest_folder.startswith('/'):
            dest_folder = '/' + dest_folder

        dest_folder = '/folder' + dest_folder

        cookie_val = cookie.split('"')[1]
        cookie = {'vmware_soap_session': cookie_val}

        params = {'dcPath' : datacenter, 'dsName' : datastore}
        url = 'https://' + host + dest_folder + '/' + iso_name

        with open(iso, 'rb') as data:
            response = requests.put(
                url, params=params, cookies=cookie, data=data, verify=verify
            )

        self.logger.info('status: %s', response.status_code)
        self.logger.debug(response.status_code, kwargs)
        return response.status_code


    def task_monitor(self, task, question=True, host=False):
        """
        Method monitors the state of called task and outputs the current status.
        Some tasks require that questions be answered before completion, and are
        optional arguments in the case that some tasks don't require them. It
        will continually check for questions while in progress. The VM object is
        required if the question argument is True.

        Args:
            task (obj):      TaskManager object
            question (bool): Enable or Disable Question
            host (obj):      VirtualMachine object
        """
        # keep track of answered questions
        answered = {}

        while task.info.state == 'running':
            while task.info.progress:
                if question and host:
                    result = self.question_and_answer(host, **answered)
                    if result:
                        answered.update(result)
                if isinstance(task.info.progress, int):
                    sys.stdout.write(
                        '\r[' + task.info.state + '] | ' + str(task.info.progress)
                    )
                    sys.stdout.flush()
                    if task.info.progress == 100:
                        sys.stdout.write(
                            '\r[' + task.info.state + '] | ' + str(task.info.progress)
                        )
                        sys.stdout.flush()
                        break
                else:
                    sys.stdout.flush()
                    break

        if task.info.state == 'error':
            sys.stdout.write('\r[' + task.info.state + '] | ' + task.info.error.msg + '\n')
            self.logger.info('[' + task.info.state + '] | ' + task.info.error.msg)
            sys.stdout.flush()

        if task.info.state == 'success':
            sys.stdout.write('\r[' + task.info.state + '] | task successfully completed.\n')
            self.logger.info('[' + task.info.state + '] | task successfully completed.')
            sys.stdout.flush()


    @classmethod
    def assign_ip(cls, dhcp=False, *static):
        """
        Method assigns a static IP on the vm

        Args:
            dhcp (bool):    Enable or Disable DHCP
            static (list): A list that contains the following:
                ipaddr, netmask, gateway, domain, dns1, dns2

        Returns:
            nic (obj): A configured object for IP assignments.  this should be
                appended to ConfigSpec devices attribute.
        """

        if dhcp:
            nic = vim.vm.customization.AdapterMapping()
            nic.adapter = vim.vm.customization.DhcpIpGenerator()

            return nic
        else:
            ipaddr = static[0]
            netmask = static[1]
            gateway = static[2]
            domain = static[3]
            dns1 = static[4]
            dns2 = static[5]
            nic.adapter = vim.vm.customization.IPSettings()
            nic.adapter.ip = vim.vm.customization.FixedIp()
            nic.adapter.ip.ipAddress = ipaddr
            nic.adapter.subnetMask = netmask
            nic.adapter.gateway = gateway
            nic.adapter.dnsDomain = domain
            nic.adapter.dnsServerList = [dns1, dns2]

            return nic

    @classmethod
    def scsi_config(cls, bus_number=0, shared_bus='noSharing'):
        """
        Method creates a SCSI Controller on the VM

        Args:
            bus_number (int): Bus number associated with this controller.
            shared_bus (str): Mode for sharing the SCSI bus.
                Valid Modes:
                    physicalSharing, virtualSharing, noSharing
        Returns:
            scsi (obj): A configured object for a SCSI Controller.  this should
                be appended to ConfigSpec devices attribute.
        """

        # randomize key for multiple scsi controllers
        key = int(uniform(-1, -100))

        scsi = vim.vm.device.VirtualDeviceSpec()
        scsi.operation = 'add'

        scsi.device = vim.vm.device.ParaVirtualSCSIController()
        scsi.device.key = key
        scsi.device.sharedBus = shared_bus
        scsi.device.busNumber = bus_number

        # grab defined key so devices can use it to connect to it.
        key = scsi.device.key

        return (key, scsi)


    @classmethod
    def cdrom_config(cls, **kwargs):
        """
        Method manages a CD-Rom Virtual Device.  If iso_path is not provided,
        then it will create the device.  Otherwise, it will attempt to mount
        the iso.  Iso must reside inside a datastore.  Use the upload_iso()
        method to use an iso stored locally.  If umount is True, then the
        method will attempt to umount the iso.

        When editing an existing device, the method will obtain the existing key
        so it can interact with the device.

        Args:
            datastore (str): Name of datastore
            iso_path (str):  Path to ISO
            iso_name (str):  Name of ISO on datastore
            umount (bool):   If True, then method will umount any existing ISO.
                If False, then method will create or mount the ISO.
            key (int): The key associated with the Cdrom device
            controller (int): The controller key associated with Cdrom device

        Returns:
            cdrom (obj): A configured object for a CD-Rom device.  this should
                be appended to ConfigSpec devices attribute.
        """
        datastore = kwargs.get('datastore', None)
        iso_path = kwargs.get('iso_path', None)
        iso_name = kwargs.get('iso_name', None)
        umount = kwargs.get('umount', None)
        key = kwargs.get('key', None)
        controller = kwargs.get('controller', None)

        cdrom = vim.vm.device.VirtualDeviceSpec()
        cdrom.device = vim.vm.device.VirtualCdrom()
        cdrom.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        cdrom.device.connectable.connected = True
        cdrom.device.connectable.startConnected = True
        cdrom.device.connectable.allowGuestControl = True

        # set default key value if it does not exist
        if not key:
            cdrom.device.key = 3002
        else:
            cdrom.device.key = key

        if not controller:
            cdrom.device.controllerKey = 201
        else:
            cdrom.device.controllerKey = controller

        # umount iso
        if umount:
            cdrom.operation = 'edit'
            cdrom.device.backing = vim.vm.device.VirtualCdrom.RemotePassthroughBackingInfo()
            cdrom.device.backing.exclusive = False

            return cdrom

        # mount iso
        if iso_path and iso_name and datastore and not umount:
            cdrom.operation = 'edit'

            if iso_path.endswith('.iso'):
                pass
            elif iso_path.endswith('/'):
                iso_path = iso_path + iso_name
            else:
                iso_path = iso_path + '/' + iso_name

            # path is relative, so we strip off the first character.
            if iso_path.startswith('/'):
                iso_path = iso_path.lstrip('/')

            cdrom.device.backing = vim.vm.device.VirtualCdrom.IsoBackingInfo()
            cdrom.device.backing.fileName = '['+ datastore + '] ' + iso_path

            return cdrom

        # create cdrom
        else:
            cdrom.operation = 'add'
            cdrom.device.backing = vim.vm.device.VirtualCdrom.RemotePassthroughBackingInfo()
            cdrom.device.backing.exclusive = False

            return cdrom


    @classmethod
    def disk_config(cls, edit=False, **kwargs):
        """
        Method returns configured VirtualDisk object

        Kwargs:
            container (obj): Cluster container object
            datastore (str): Name of datastore for the disk files location.
            size (int):      Integer of disk in kilobytes
            key  (int):      Integer value of scsi device
            unit (int):      unitNumber of device.
            mode (str):      The disk persistence mode.
            thin (bool):     If True, then it enables thin provisioning

        Returns:
            disk (obj): A configured object for a VMDK Disk.  this should
                be appended to ConfigSpec devices attribute.
        """
        # capacityInKB is deprecated but also a required field. See pyVmomi bug #218

        container = kwargs.get('container', None)
        datastore = kwargs.get('datastore', None)
        size = kwargs.get('size', None)
        key = kwargs.get('key', None)
        unit = kwargs.get('unit', 0)
        mode = kwargs.get('mode', 'persistent')
        thin = kwargs.get('thin', True)
        controller = kwargs.get('controller', None)
        filename = kwargs.get('filename', None)

        disk = vim.vm.device.VirtualDeviceSpec()

        if edit:
            disk.operation = 'edit'

            disk.device = vim.vm.device.VirtualDisk()
            disk.device.capacityInKB = size
            disk.device.key = key
            # controllerKey is tied to SCSI Controller
            disk.device.controllerKey = controller
            disk.device.unitNumber = unit
            disk.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
            disk.device.backing.fileName = filename
            disk.device.backing.diskMode = mode

        else:
            disk.operation = 'add'
            disk.fileOperation = 'create'

            disk.device = vim.vm.device.VirtualDisk()
            disk.device.capacityInKB = size
            # controllerKey is tied to SCSI Controller
            disk.device.controllerKey = controller
            disk.device.unitNumber = unit
            disk.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
            disk.device.backing.fileName = '['+datastore+']'
            disk.device.backing.datastore = Query.get_obj(container, datastore)
            disk.device.backing.diskMode = mode
            disk.device.backing.thinProvisioned = thin
            disk.device.backing.eagerlyScrub = False

        return disk

    @classmethod
    def nic_config(cls, edit=False, **kwargs):
        """
        Method returns configured object for network interface.

        kwargs:
            container (obj):  ContainerView object.
            network (str):    Name of network to add to VM.
            connected (bool): Indicates that the device is currently
                connected. Valid only while the virtual machine is running.
            start_connected (bool):
                Specifies whether or not to connect the device when the
                virtual machine starts.
            allow_guest_control (bool):
                Allows the guest to control whether the connectable device
                is connected.
            driver (str): A str that represents a network adapter driver
        Returns:
            nic (obj): A configured object for a Network device.  this should
                be appended to ConfigSpec devices attribute.
        """
        key = kwargs.get('key', None)
        controller = kwargs.get('controller', None)
        container = kwargs.get('container', None)
        mac_address = kwargs.get('mac_address', None)
        network = kwargs.get('network', None)
        connected = kwargs.get('connected', True)
        start_connected = kwargs.get('start_connected', True)
        allow_guest_control = kwargs.get('allow_get_control', True)
        unit = kwargs.get('unit', None)
        address_type = kwargs.get('address_type', 'assigned')
        driver = kwargs.get('driver', 'VirtualVmxnet3')

        nic = vim.vm.device.VirtualDeviceSpec()
        nic.device = getattr(vim.vm.device, driver)()

        if edit:
            nic.operation = 'edit'
            nic.device.key = key
            nic.device.controllerKey = controller
            nic.device.macAddress = mac_address
            nic.device.unitNumber = unit
            nic.device.addressType = address_type
        else:
            nic.operation = 'add'

        nic.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
        nic.device.backing.network = Query.get_obj(container, network)
        nic.device.backing.deviceName = network

        nic.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        nic.device.connectable.connected = connected
        nic.device.connectable.startConnected = start_connected
        nic.device.connectable.allowGuestControl = allow_guest_control

        return nic

    def create(self, folder, datastore, pool, **config):
        """
        Method creates the VM.

        Args:
            folder (obj):    Folder object where the VM will reside
            pool (obj):      ResourcePool object
            datastore (str): Datastore for vmx files
            config (dict):   A dict containing vim.vm.ConfigSpec attributes
        """

        vmxfile = vim.vm.FileInfo(vmPathName='[' + datastore + ']')
        config.update({'files' : vmxfile})
        task = folder.CreateVM_Task(config=vim.vm.ConfigSpec(**config), pool=pool)

        self.logger.info('%s', config['name'])
        self.logger.debug('%s %s %s %s', folder, datastore, pool, config)

        self.task_monitor(task, False)


    def reconfig(self, host, **config):
        """
        Method reconfigures a VM.

        Args:
            host (obj):    VirtualMachine object
            config (dict): A dictionary of vim.vm.ConfigSpec attributes and
                their values.
        """

        self.logger.debug('%s %s', host.name, config)
        task = host.ReconfigVM_Task(vim.vm.ConfigSpec(**config))
        self.task_monitor(task, True, host)


    def power(self, host, state):
        """
        Method manages power states.

        Args:
            host (obj):  VirtualMachine object
            state (str): options are: on,off,reset,rebootshutdown
        """
        self.logger.info('%s %s', host.name, state)
        if state == 'off':
            self.task_monitor(host.PowerOff(), True, host)

        if state == 'on':
            self.task_monitor(host.PowerOn(), True, host)

        if state == 'reset':
            self.task_monitor(host.Reset(), True, host)

        if state == 'reboot':
            self.task_monitor(host.RebootGuest(), True, host)

        if state == 'shutdown':
            host.ShutdownGuest()


    def mvfolder(self, host, folder):
        """
        Method relocate a VM to another folder.

        Args:
            host (list):   List of VirtualMachine objects
            folder (obj):  Folder object
        """

        self.logger.info('Move VM %s to %s folder', host.name, folder.name)
        task = folder.MoveIntoFolder_Task([host])
        self.task_monitor(task, True, host)
