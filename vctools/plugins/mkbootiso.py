#!/usr/bin/python
"""Plugin for creating a boot iso on a per server basis."""
from __future__ import print_function
import logging
import subprocess
import textwrap
import sys

class MkBootISO(object):
    """
    Makes a static IP per host boot iso for easier network host creation when
    PXE booting or DHCP networks are not an option.
    """

    def __init__(self):
        pass

    @staticmethod
    def sanity_ip_checker(**kwargs):
        """
        Ensure ip doesn't match a subset of rules
        """
        if kwargs['ip'].endswith('.1'):
            raise ValueError('%s seems to conflict with router devices.' % kwargs['ip'])

    @classmethod
    def updateiso(cls, source, ks_url, sanity=True, **kwargs):
        """
        Update iso image with host specific parameters.
        All kickstart options will be added from a yaml file.
        """

        label = """
            default vesamenu.c32
            display boot.msg
            timeout 5
            label iso created by mkbootiso
            menu default
            kernel vmlinuz
            append initrd=initrd.img %s %s

            """ % ('ks=' + ks_url,
                   ' '.join("%s=%s" % (key, val) for (key, val) in kwargs.iteritems()))

        if sanity:
            try:
                MkBootISO.sanity_ip_checker(**kwargs)
                with open(source + '/isolinux/isolinux.cfg', 'w') as iso_cfg:
                    iso_cfg.write(textwrap.dedent(label).strip())
            except ValueError as err:
                print(err)
                answer = raw_input('Continue? [y|n]')
                if 'Y' or 'y' in answer:
                    pass
                else:
                    print('Exiting...')
                    sys.exit(1)
        else:
            with open(source + '/isolinux/isolinux.cfg', 'w') as iso_cfg:
                iso_cfg.write(textwrap.dedent(label).strip())


    @classmethod
    def createiso(cls, source, output, filename):
        """create iso image."""
        cmd = [
            '/usr/bin/genisoimage', '-quiet', '-J', '-T', '-o', output + '/' + filename,
            '-b', 'isolinux/isolinux.bin', '-c', 'isolinux/boot.cat', '-no-emul-boot',
            '-boot-load-size', '4', '-boot-info-table', '-R', '-m', 'TRANS.TBL', '-graft-points',
            source,
        ]

        subprocess.call(cmd)

    @classmethod
    def load_template(cls, cfg, template=None):
        """
        Returns dict if template is found. Mkbootiso can be configured to use
        a special "templates" key, for creating specific kickstart parameters
        across different environments.  This method will return the dict whose
        parent matches template.

        Example:
            mkbootiso:
              templates:
                rhel7:
                  source: 'https://ks.hostname.com/rhel7
                rhel6:
                  source: 'https://ks.hostname.com/rhel6

        Args:
            cfgs (dict): Dictionary to load as cfg
            template (bool): If template is set, it will attempt to match the
                config labeled as template and load that cfg

        Returns: A dictionary of configured options for creating an ISO
        """

        if template:
            if 'templates' in cfg:
                if template in cfg['templates']:
                    return cfg['templates'][template]
