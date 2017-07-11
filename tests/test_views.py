import json

import pytest

from utilery.models import Layer, Recipe
from .utils import copy


@pytest.mark.asyncio
async def test_simple_request(req, fetchall):

    def check_query(query, *args, **kwargs):
        assert 'SELECT' in query
        assert 'ST_Intersection' not in query
        assert 'ST_Expand' not in query

    fetchall([], check_query)

    resp = await req('/all/0/0/0/pbf')
    assert resp.status == b'200 OK'


@pytest.mark.asyncio
async def test_options(req, fetchall):
    resp = await req('/all/0/0/0/pbf', method='OPTIONS')
    assert resp.status == b'200 OK'


@pytest.mark.asyncio
async def test_unknown_layer_returns_400(req):

    resp = await req('/unknown/0/0/0/pbf')
    assert resp.status == b'400 Bad Request'


@pytest.mark.asyncio
async def test_unknown_recipe_returns_400(req):

    resp = await req('/unknown/all/0/0/0/pbf')
    assert resp.status == b'400 Bad Request'


@pytest.mark.asyncio
async def test_unknown_path_returns_404(req):

    resp = await req('/all/0/0/0.xyz')
    assert resp.status == b'404 Not Found'


@pytest.mark.asyncio
async def test_can_request_one_layer(req, fetchall):

    def check_query(query, *args, **kwargs):
        assert 'SELECT' in query

    fetchall([], check_query)

    resp = await req('/mylayer/0/0/0/pbf')
    assert resp.status == b'200 OK'


@pytest.mark.asyncio
async def test_can_use_recipe_in_url(req, fetchall):

    fetchall([])

    resp = await req('/default/mylayer/0/0/0/pbf')
    assert resp.status == b'200 OK'


@pytest.mark.asyncio
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
    assert resp.status == b'200 OK'


@pytest.mark.asyncio
async def test_can_ask_several_layers(req, fetchall, recipes):

    fetchall([])
    recipe = Recipe(copy(recipes['default']))
    layer = Layer(recipe, copy(recipes['default'].layers['mylayer']))
    layer['name'] = 'other'
    recipe.layers['other'] = layer
    recipes['default'] = recipe

    resp = await req('/mylayer+other/0/0/0/pbf')
    assert resp.status == b'200 OK'


@pytest.mark.asyncio
async def test_does_not_request_if_lower_than_minzoom(req, fetchall, layer):

    layer['queries'].append({
        'sql': 'SELECT geometry AS way, type, name FROM youdontwantme',
        'minzoom': 9
    })

    def check_query(query, *args, **kwargs):
        assert "youdontwantme" not in query

    fetchall([], check_query)

    assert await req('/all/0/0/0/pbf')


@pytest.mark.asyncio
async def test_does_not_request_if_higher_than_maxzoom(req, fetchall, layer):

    layer['queries'].append({
        'sql': 'SELECT geometry AS way, type, name FROM youdontwantme',
        'maxzoom': 1
    })

    def check_query(query, *args, **kwargs):
        assert "youdontwantme" not in query

    fetchall([], check_query)

    assert await req('/all/2/0/0/pbf')


@pytest.mark.asyncio
async def test_can_change_srid(req, fetchall, layer):

    layer['srid'] = 900913

    def check_query(query, *args, **kwargs):
        assert "900913" in query

    fetchall([], check_query)

    assert await req('/all/0/0/0/pbf')


@pytest.mark.asyncio
async def test_clip_when_asked(req, fetchall, layer):

    layer['clip'] = True

    def check_query(query, *args, **kwargs):
        assert "ST_Intersection" in query

    fetchall([], check_query)

    assert await req('/all/0/0/0/pbf')


@pytest.mark.asyncio
async def test_add_buffer_when_asked(req, fetchall, layer):

    layer['buffer'] = 128

    def check_query(query, *args, **kwargs):
        assert "ST_Expand" in query

    fetchall([], check_query)

    assert await req('/all/0/0/0/pbf')


@pytest.mark.asyncio
async def test_tilejson(req, config):
    config.TILEJSON['name'] = "testname"
    resp = await req('/tilejson/mvt.json')
    assert resp.status == b'200 OK'
    data = json.loads(resp.body)
    assert data['name'] == "testname"
    assert "vector_layers" in data
    assert data['vector_layers'][0]['id'] == 'default:mylayer'
