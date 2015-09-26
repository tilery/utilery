import pytest
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from utilery.models import Recipe
from .utils import copy

# Do not import anything that can import config before we can patch it.


class TestPlugin(object):

    def on_before_load(self, config):
        config.BEFORE_LOAD = True

    def on_load(self, config, recipes):
        assert config.BEFORE_LOAD
        config.LOAD = True


def pytest_configure(config):
    from utilery import config as uconfig
    uconfig.RECIPES = []
    uconfig.PLUGINS = [TestPlugin]
    from utilery import core
    core.RECIPES['default'] = Recipe({
        'name': 'default',
        'layers': [{
            'name': 'mylayer',
            'queries': [
                {
                    'sql': 'SELECT geometry AS way, type, name FROM osm_landusages_gen0',  # noqa
                    'maxzoom': 9
                }
            ]
        }]
    })


@pytest.fixture
def fetchall(monkeypatch):

    def _(result, check=None):
        def func(*args, **kwargs):
            if check:
                check(*args, **kwargs)
            return result
        monkeypatch.setattr('utilery.core.DB.fetchall', func)

    return _


@pytest.fixture
def client():
    from utilery.views import app
    return Client(app, BaseResponse)


class MonkeyPatchWrapper(object):
    def __init__(self, monkeypatch, wrapped_object):
        super().__setattr__('monkeypatch', monkeypatch)
        super().__setattr__('wrapped_object', wrapped_object)

    def __getattr__(self, attr):
        return getattr(self.wrapped_object, attr)

    def __getitem__(self, item):
        return self.wrapped_object.get(item)

    def __setattr__(self, attr, value):
        self.monkeypatch.setattr(self.wrapped_object, attr, value,
                                 raising=False)

    def __setitem__(self, item, value):
        self.monkeypatch.setitem(self.wrapped_object, item, value)

    def __delattr__(self, attr):
        self.monkeypatch.delattr(self.wrapped_object, attr)

    def __delitem__(self, item):
        self.monkeypatch.delitem(self.wrapped_object, item)


@pytest.fixture
def recipes(monkeypatch):
    from utilery import core
    return MonkeyPatchWrapper(monkeypatch, core.RECIPES)


@pytest.fixture()
def config(monkeypatch):
    from utilery import config as uconfig
    return MonkeyPatchWrapper(monkeypatch, uconfig)


@pytest.fixture
def layer(recipes):
    recipe = Recipe(copy(recipes['default']))
    recipes['default'] = recipe
    layer = recipe.layers['mylayer']
    return layer


@pytest.fixture
def plugins(monkeypatch):
    from utilery.plugins import Plugins

    # Reset plugins.
    monkeypatch.setattr(Plugins, '_registry', [])
    monkeypatch.setattr(Plugins, '_hooks', {})

    return lambda p: Plugins.register_plugin(p)
