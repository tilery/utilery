from copy import deepcopy
import os
from pathlib import Path

import pytest

from .utils import copy
# Do not import anything that can import config before we can patch it.


def pytest_configure(config):
    path = Path(str(config.rootdir)) / 'utilery/config/test.py'
    config.OLD_UTILERY_SETTINGS = os.environ.get('UTILERY_SETTINGS')
    os.environ['UTILERY_SETTINGS'] = str(path)
    from utilery import config as uconfig
    uconfig.RECIPES = []
    from utilery import core
    from utilery.models import Recipe
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


def pytest_unconfigure(config):
    os.environ['UTILERY_SETTINGS'] = config.OLD_UTILERY_SETTINGS or ''


@pytest.yield_fixture
def app():
    from utilery.views import app as myapp
    hooks = deepcopy(myapp.hooks)
    yield myapp
    myapp.hooks = hooks


@pytest.fixture
def fetchall(monkeypatch):

    def _(result, check=None):
        async def func(*args, **kwargs):
            if check:
                check(*args, **kwargs)
            return result
        monkeypatch.setattr('utilery.core.DB.fetchall', func)

    return _


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
    from utilery.models import Recipe
    recipe = Recipe(copy(recipes['default']))
    recipes['default'] = recipe
    layer = recipe.layers['mylayer']
    return layer
