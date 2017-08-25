import json
from http import HTTPStatus

import pytest
from utilery.models import Layer, Recipe

from .utils import copy

pytestmark = pytest.mark.asyncio


async def test_simple_request(req, fetchall):
    fetchall([])
    resp = await req('/all/0/0/0/pbf')
    assert resp.status == HTTPStatus.OK


async def test_options(req, fetchall):
    resp = await req('/all/0/0/0/pbf', method='OPTIONS')
    assert resp.status == HTTPStatus.OK


async def test_unknown_layer_returns_400(req):
    resp = await req('/unknown/0/0/0/pbf')
    assert resp.status == HTTPStatus.BAD_REQUEST


async def test_unknown_recipe_returns_400(req):

    resp = await req('/unknown/all/0/0/0/pbf')
    assert resp.status == HTTPStatus.BAD_REQUEST


async def test_unknown_path_returns_404(req):

    resp = await req('/all/0/0/0.xyz')
    assert resp.status == HTTPStatus.NOT_FOUND


async def test_can_request_one_layer(req, fetchall):

    def check_query(query, *args, **kwargs):
        assert 'SELECT' in query

    fetchall([], check_query)

    resp = await req('/mylayer/0/0/0/pbf')
    assert resp.status == HTTPStatus.OK


async def test_can_use_recipe_in_url(req, fetchall):

    fetchall([])

    resp = await req('/default/mylayer/0/0/0/pbf')
    assert resp.status == HTTPStatus.OK


async def test_can_ask_for_specific_recipe_layers(req, fetchall, recipes):

    def check_query(query, *args, **kwargs):
        assert 'yetanother' in query

    fetchall([], check_query)

    recipe = Recipe(copy(recipes['default']))
    layer = Layer(recipe, copy(recipes['default'].layers['mylayer']))
    layer.queries[0]['sql'] = 'SELECT * FROM yetanother'
    recipe.layers['mylayer'] = layer
    recipe['name'] = 'other'
    recipes['other'] = recipe

    resp = await req('/other/mylayer/0/0/0/pbf')
    assert resp.status == HTTPStatus.OK


async def test_can_ask_several_layers(req, fetchall, recipes):

    fetchall([])
    recipe = Recipe(copy(recipes['default']))
    layer = Layer(recipe, copy(recipes['default'].layers['mylayer']))
    layer['name'] = 'other'
    recipe.layers['other'] = layer
    recipes['default'] = recipe

    resp = await req('/mylayer+other/0/0/0/pbf')
    assert resp.status == HTTPStatus.OK


async def test_tilejson(req, config):
    config.TILEJSON['name'] = "testname"
    resp = await req('/tilejson/mvt.json')
    assert resp.status == HTTPStatus.OK
    data = json.loads(resp.body)
    assert data['name'] == "testname"
    assert "vector_layers" in data
    assert data['vector_layers'][0]['id'] == 'default:mylayer'
