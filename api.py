#!/usr/bin/python
# vim: et ts=4 sw=4
""" An API for curl enthusiasts."""
api = Flask(__name__)
# allow trailing slash or not
api.url_map.strict_slashes = False

@api.route('/')
def root():
    """
    vctools API

    GET /api/<command> Returns information on how to use command.

    command:
        create        Create a new virtual machine
        mkbootiso     Create a boot.iso on a per server basis.
        mount         Mount an iso on a virtual machine.
        power         Configure power state for virtual machine.
        reconfig      Reconfigure attributes on an existing virtual machine.
        umount        Unmount an iso on a virtual machine.
        upload        Upload a boot.iso to a remote datastore.

    """
    return textwrap.dedent(root.__doc__)

if __name__ == '__main__':
    api.run(threaded=True)
