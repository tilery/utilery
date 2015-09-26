import json

from utilery.models import Layer, Recipe
from .utils import copy


def test_simple_request(client, fetchall):

    def check_query(query, *args, **kwargs):
        assert 'SELECT' in query
        assert 'ST_Intersection' not in query
        assert 'ST_Expand' not in query

    fetchall([], check_query)

    resp = client.get('/all/0/0/0.pbf')
    assert resp.status_code == 200


def test_unknown_layer_return_400(client):

    resp = client.get('/unknown/0/0/0.pbf')
    assert resp.status_code == 400


def test_can_request_one_layer(client, fetchall):

    def check_query(query, *args, **kwargs):
        assert 'SELECT' in query

    fetchall([], check_query)

    resp = client.get('/mylayer/0/0/0.pbf')
    assert resp.status_code == 200


def test_can_use_recipe_in_url(client, fetchall):

    fetchall([])

    resp = client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status_code == 200


def test_can_ask_for_specific_recipe_layers(client, fetchall, recipes):

    def check_query(query, *args, **kwargs):
        assert 'yetanother' in query

    fetchall([], check_query)

    recipe = Recipe(copy(recipes['default']))
    layer = Layer(recipe, copy(recipes['default'].layers['mylayer']))
    layer.queries[0]['sql'] = 'SELECT * FROM yetanother'
    recipe.layers['mylayer'] = layer
    recipe['name'] = 'other'
    recipes['other'] = recipe

    resp = client.get('/other/mylayer/0/0/0.pbf')
    assert resp.status_code == 200


def test_can_ask_several_layers(client, fetchall, recipes):

    fetchall([])
    recipe = Recipe(copy(recipes['default']))
    layer = Layer(recipe, copy(recipes['default'].layers['mylayer']))
    layer['name'] = 'other'
    recipe.layers['other'] = layer
    recipes['default'] = recipe

    resp = client.get('/mylayer+other/0/0/0.pbf')
    assert resp.status_code == 200


def test_does_not_request_if_lower_than_minzoom(client, fetchall, layer):

    layer['queries'].append({
        'sql': 'SELECT geometry AS way, type, name FROM youdontwantme',
        'minzoom': 9
    })

    def check_query(query, *args, **kwargs):
        assert "youdontwantme" not in query

    fetchall([], check_query)

    assert client.get('/all/0/0/0.pbf')


def test_does_not_request_if_higher_than_maxzoom(client, fetchall, layer):

    layer['queries'].append({
        'sql': 'SELECT geometry AS way, type, name FROM youdontwantme',
        'maxzoom': 1
    })

    def check_query(query, *args, **kwargs):
        assert "youdontwantme" not in query

    fetchall([], check_query)

    assert client.get('/all/2/0/0.pbf')


def test_can_change_srid(client, fetchall, layer):

    layer['srid'] = 900913

    def check_query(query, *args, **kwargs):
        assert "900913" in query

    fetchall([], check_query)

    assert client.get('/all/0/0/0.pbf')


def test_clip_when_asked(client, fetchall, layer):

    layer['clip'] = True

    def check_query(query, *args, **kwargs):
        assert "ST_Intersection" in query

    fetchall([], check_query)

    assert client.get('/all/0/0/0.pbf')


def test_add_buffer_when_asked(client, fetchall, layer):

    layer['buffer'] = 128

    def check_query(query, *args, **kwargs):
        assert "ST_Expand" in query

    fetchall([], check_query)

    assert client.get('/all/0/0/0.pbf')


def test_tilejson(client, config):
    config.TILEJSON['name'] = "testname"
    resp = client.get('/tilejson/mvt.json')
    assert resp.status_code == 200
    data = json.loads(resp.data.decode())
    assert data['name'] == "testname"
    assert "vector_layers" in data
    assert data['vector_layers'][0]['id'] == 'default:mylayer'
