import json
from http import HTTPStatus

import pytest
from utilery.models import Layer, Recipe

from .utils import copy

pytestmark = pytest.mark.asyncio


async def test_simple_request(client, fetchall):
    fetchall([])
    resp = await client.get('/all/0/0/0.pbf')
    assert resp.status == HTTPStatus.OK


async def test_options(client, fetchall):
    resp = await client.options('/all/0/0/0.pbf')
    assert resp.status == HTTPStatus.OK


async def test_unknown_layer_returns_400(client):
    resp = await client.get('/unknown/0/0/0.pbf')
    assert resp.status == HTTPStatus.BAD_REQUEST


async def test_unknown_recipe_returns_400(client):

    resp = await client.get('/unknown/all/0/0/0.pbf')
    assert resp.status == HTTPStatus.BAD_REQUEST


async def test_unknown_path_returns_404(client):

    resp = await client.get('/all/0/0/0.xyz')
    assert resp.status == HTTPStatus.NOT_FOUND


async def test_can_request_one_layer(client, fetchall):

    def check_query(query, *args, **kwargs):
        assert 'SELECT' in query

    fetchall([], check_query)

    resp = await client.get('/mylayer/0/0/0.pbf')
    assert resp.status == HTTPStatus.OK


async def test_can_use_recipe_in_url(client, fetchall):

    fetchall([])

    resp = await client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status == HTTPStatus.OK


async def test_can_ask_for_specific_recipe_layers(client, fetchall, recipes):

    def check_query(query, *args, **kwargs):
        assert 'yetanother' in query

    fetchall([], check_query)

    recipe = Recipe(copy(recipes['default']))
    layer = Layer(recipe, copy(recipes['default'].layers['mylayer']))
    layer.queries[0]['sql'] = 'SELECT * FROM yetanother'
    recipe.layers['mylayer'] = layer
    recipe['name'] = 'other'
    recipes['other'] = recipe

    resp = await client.get('/other/mylayer/0/0/0.pbf')
    assert resp.status == HTTPStatus.OK


async def test_can_ask_several_layers(client, fetchall, recipes):

    fetchall([])
    recipe = Recipe(copy(recipes['default']))
    layer = Layer(recipe, copy(recipes['default'].layers['mylayer']))
    layer['name'] = 'other'
    recipe.layers['other'] = layer
    recipes['default'] = recipe

    resp = await client.get('/mylayer+other/0/0/0.pbf')
    assert resp.status == HTTPStatus.OK


async def test_tilejson(client, config):
    config.TILEJSON['name'] = "testname"
    resp = await client.get('/tilejson/mvt.json')
    assert resp.status == HTTPStatus.OK
    data = json.loads(resp.body)
    assert data['name'] == "testname"
    assert "vector_layers" in data
    assert data['vector_layers'][0]['id'] == 'default:mylayer'
