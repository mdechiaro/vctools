#!/usr/bin/python
# vim: ts=4 sw=4 et
""" Logging metaclass."""
import logging

class Log(type):
    """ Metaclass that will load all plugins. """
    def __init__(cls, name, args, kwargs):
        """
        Args:
            name (str): Becomes __name__ attribute
            args (tuple): Becomes __bases__ attribute
            kwargs (dict): Becomes __dict__ attribute
        """
        super(Log, cls).__init__(name, args, kwargs)

        cls.logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class Logger(object):
    """ Allows any class to easily have logging. """
    __metaclass__ = Log
