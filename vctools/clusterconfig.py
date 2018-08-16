#!/usr/bin/env python
# vim: ts=4 sw=4 et
"""Various config options for Virtual Machines."""


from pyVmomi import vim # pylint: disable=E0611
from vctools.query import Query
from vctools import Logger
from vctools.tasks import Tasks

class ClusterConfig(Logger):
    """Various config options for Virtual Machines."""
    def __init__(self, auth, opts, dotrc):
        self.auth = auth
        self.opts = opts
        self.dotrc = dotrc

    def drs_rule(self):
        """
        Method messes with DRS rules.
        Currently only Anti Affinity rules, and only add or delete.

        For safety, it has a concept of a vctools prefix.  The prefix lives in the
        rc file, or can be declared by a flag.  This is so you "can't" delete a
        rule that was not created by vctools.

        Args:
            cluster (str): cluster to modify
            type (str): currently only anti-affinity
            oper (add|delete): operation mode
            name (str): name of the rule
            vms (list): list of vms (to add, not used for delete)

        Returns true if successful.
        """
        cluster = self.opts.cluster
        drs_type = self.opts.drs_type
        name = self.opts.name
        vms = self.opts.vms
        function = self.opts.function


        self.logger.debug(cluster, drs_type, name, vms, function)

        # containers we need
        clusters = Query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.ComputeResource], True
        )
        virtual_machines = Query.create_container(
            self.auth.session, self.auth.session.content.rootFolder,
            [vim.VirtualMachine], True
        )

        # our cluster object
        cluster_obj = Query.get_obj(clusters.view, cluster)

        if drs_type == 'anti-affinity':

            if function == 'add':

                vm_obj_list = []
                for vm_obj in vms:
                    vm_obj_list.append(Query.get_obj(virtual_machines.view, vm_obj))

                # check to see if this rule name is in use
                if Query.is_anti_affinity_rule(cluster_obj, name):
                    raise ValueError('Error: rule name "%s" is already in use' % name)

                # check to see vms are in the right cluster
                for vm_obj in vm_obj_list:
                    if not Query.is_vm_in_cluster(cluster_obj, vm_obj):
                        raise ValueError(
                            'Error: the vm "%s" is not in the stated cluster' % vm_obj.name
                        )

                # check to see if the vms already have DRS rules
                for vm_obj in vm_obj_list:
                    match = 0
                    for rule in cluster_obj.configuration.rule:
                        if hasattr(rule, 'vm'):
                            for rulevm in rule.vm:
                                if vm_obj == rulevm:
                                    match = 1
                    if match != 0:
                        raise ValueError(
                            'Error: the vm "%s" is already in a DRS rule' % vm_obj.name
                        )

                new_rule = vim.ClusterAntiAffinityRuleSpec()
                new_rule.name = name

                new_rule.userCreated = True
                new_rule.enabled = True
                for vm_obj in vm_obj_list:
                    new_rule.vm.append(vm_obj)

                rule_spec = vim.cluster.RuleSpec(info=new_rule, operation='add')
                config_spec = vim.cluster.ConfigSpecEx(rulesSpec=[rule_spec])
                Tasks.task_monitor(cluster_obj.ReconfigureComputeResource_Task(
                    config_spec, modify=True), False)

                self.logger.info('new AA DRS rule on %s: %s', cluster, name)


            if function == 'delete':
            #Delete an AntiAffinity Rule
                # check to see if this rule name is in use, and delete if found
                found = False
                for existing_rule in cluster_obj.configuration.rule:
                    if existing_rule.name == name:
                        found = True
                        # doublecheck this is an AA rule
                        if isinstance(existing_rule, vim.cluster.AntiAffinityRuleSpec):
                            rule_spec = vim.cluster.RuleSpec(
                                removeKey=existing_rule.key, operation='remove')
                            config_spec = vim.cluster.ConfigSpecEx(rulesSpec=[rule_spec])
                            Tasks.task_monitor(cluster_obj.ReconfigureComputeResource_Task(
                                config_spec, modify=True), False)
                            self.logger.info('Deleted AA DRS rule on %s: %s', cluster, name)
                        else:
                            raise ValueError(
                                'Error: rule name "%s" not an AntiAffinity rule' % name
                            )
                if not found:
                    raise ValueError('Error: rule name "%s" not found' % name)
