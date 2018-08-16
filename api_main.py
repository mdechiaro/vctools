#!/usr/bin/python
# vim: et ts=4 sw=4
""" An API for curl enthusiasts."""

import textwrap
from flask import Flask
#
from api.mkbootiso import mkbootiso

vctools_api = Flask(__name__)

# allow trailing slash or not
vctools_api.url_map.strict_slashes = False
#
vctools_api.register_blueprint(mkbootiso, url_prefix='/mkbootiso')

@vctools_api.route('/')
def root():
    """
    vctools API

    GET /api/<command> Returns information on how to use command.

    command:
        mkbootiso     Create a boot.iso on a per server basis.

    """
    return textwrap.dedent(root.__doc__)

if __name__ == '__main__':
    vctools_api.run(threaded=True)
