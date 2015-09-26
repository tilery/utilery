from utilery.utils import import_by_path


def test_import_by_path_should_return_module_from_path():
    assert import_by_path('utilery.utils.import_by_path') == import_by_path


def test_import_by_path_should_return_module_if_given():
    assert import_by_path(import_by_path) == import_by_path
