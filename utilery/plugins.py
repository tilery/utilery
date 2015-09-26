from .utils import import_by_path
from . import config


class Plugins(object):

    _ = []

    @classmethod
    def load(cls):
        for path in config.PLUGINS:
            cls._.append(import_by_path(path)())

    @classmethod
    def send(cls, signal, *args, **kwargs):
        key = 'on_%s' % signal
        for plugin in cls._:
            if hasattr(plugin, key):
                output = getattr(plugin, key)(*args, **kwargs)
                if output:
                    return output
