#!/usr/bin/python
"""Plugin for creating a boot iso on a per server basis."""
import subprocess
import textwrap

class MkBootISO(object):
    """
    Makes a static IP per host boot iso for easier network host creation when
    PXE booting or DHCP networks are not an option.
    """

    def __init__(self):
        pass

    @classmethod
    def updateiso(cls, source, ks_url, **kwargs):
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

            """ % (ks_url, ' '.join("%s=%s" % (key, val)
                for (key, val) in kwargs.iteritems())
            )

        with open(source + '/isolinux/isolinux.cfg', 'w') as iso_cfg:
            iso_cfg.write(textwrap.dedent(label).strip())


    @classmethod
    def createiso(cls, source, output, filename):
        """create iso image."""
        cmd = ['/usr/bin/genisoimage',
               '-J',
               '-T',
               '-o', output + '/' + filename,
               '-b', 'isolinux/isolinux.bin',
               '-c', 'isolinux/boot.cat',
               '-no-emul-boot',
               '-boot-load-size', '4',
               '-boot-info-table', '-R',
               '-m', 'TRANS.TBL',
               '-graft-points', source,
        ]

        subprocess.call(cmd)
