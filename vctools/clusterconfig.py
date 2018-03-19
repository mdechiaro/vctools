"""Various config options for Virtual Machines."""
#!/usr/bin/python
# vim: ts=4 sw=4 et
from __future__ import print_function
from __future__ import division
from pyVmomi import vim # pylint: disable=E0611
from vctools.query import Query
from vctools.vmconfig import VMConfig
from vctools import Logger

class ClusterConfig(VMConfig, Logger):
    """Various config options for Virtual Machines."""
    def __init__(self, auth, opts, dotrc):
        self.auth = auth
        self.opts = opts
        self.dotrc = dotrc
        self.datacenters = Query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.Datacenter], True
        )
        self.clusters = Query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.ComputeResource], True
        )
        self.folders = Query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.Folder], True
        )
        self.virtual_machines = Query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.VirtualMachine], True
        )
        # stealing task_monitor from VMConfig
        VMConfig.__init__(self)


    def add_aa_rule(self):
        """Add an AntiAffinity Rule"""

        cluster = self.opts.cluster
        rule_name_raw = self.opts.name
        vms_raw = self.opts.vms
        self.logger.debug(cluster, rule_name_raw, vms_raw)

        # if name doesn't start with vctools-, make it
        if rule_name_raw.startswith('vctools-'):
            rule_name = rule_name_raw
        else:
            rule_name = 'vctools-' + rule_name_raw

        vm_obj_list = []
        for vm_obj in vms_raw:
            vm_obj_list.append(Query.get_obj(self.virtual_machines.view, vm_obj))
        cluster_obj = Query.get_obj(self.clusters.view, cluster)

        # check to see if this rule name is in use
        for existing_rule in cluster_obj.configuration.rule:
            if existing_rule.name == rule_name:
                raise ValueError('Error: rule name "%s" is already in use' % rule_name)

        # check to see vms are in the right cluster
        for vm_obj in vm_obj_list:
            match = 0
            for clus_vm in cluster_obj.resourcePool.vm:
                if vm_obj == clus_vm:
                    #print('found match: ', vm_obj)
                    match = 1
            if match == 0:
                raise ValueError('Error: the vm "%s" is not in the stated cluster' % vm_obj.name)

        # check to see if the vms already have DRS rules
        for vm_obj in vm_obj_list:
            match = 0
            for rule in cluster_obj.configuration.rule:
                if hasattr(rule, 'vm'):
                    for rulevm in rule.vm:
                        if vm_obj == rulevm:
                            match = 1
            if match != 0:
                raise ValueError('Error: the vm "%s" is already in a DRS rule' % vm_obj.name)

        new_rule = vim.ClusterAntiAffinityRuleSpec()
        new_rule.name = rule_name

        new_rule.userCreated = True
        new_rule.enabled = True
        for vm_obj in vm_obj_list:
            new_rule.vm.append(vm_obj)

        #do the needful
        rule_spec = vim.cluster.RuleSpec(info=new_rule, operation='add')
        config_spec = vim.cluster.ConfigSpecEx(rulesSpec=[rule_spec])
        self.task_monitor(cluster_obj.ReconfigureComputeResource_Task(
            config_spec, modify=True), False)

        self.logger.info('new AA DRS rule on %s: %s', cluster, rule_name)
