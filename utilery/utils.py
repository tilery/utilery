from importlib import import_module


def import_by_path(path):
    """
    Import functions or class by their path. Should be of the form:
    path.to.module.func
    """
    if not isinstance(path, str):
        return path
    module_path, name = path.rsplit('.', 1)
    module = import_module(module_path)
    attr = getattr(module, name)
    return attr
