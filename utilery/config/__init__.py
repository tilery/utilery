import imp
import os

from .default import *  # noqa

# Try to load local setting from a local path.
localpath = os.environ.get('UTILERY_SETTINGS')
if localpath:
    d = imp.new_module('config')
    d.__file__ = localpath
    try:
        with open(localpath) as config_file:
            exec(compile(config_file.read(), localpath, 'exec'), d.__dict__)
    except IOError as e:
        print('Unable to import', localpath, 'from', 'UTILERY_SETTINGS')
    else:
        print('Loaded local config from', localpath)
        for key in dir(d):
            if key.isupper():
                globals()[key] = getattr(d, key)
