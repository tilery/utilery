from http import HTTPStatus

import pytest

from utilery.core import app


@app.listen('before_load')
async def on_before_load(config):
    config.BEFORE_LOAD = True


@app.listen('load')
async def on_load(config, recipes):
    assert config.BEFORE_LOAD
    config.LOAD = True


def test_on_before_load(client, config):
    assert config.BEFORE_LOAD


def test_on_load(client, config):
    assert config.LOAD


@pytest.mark.asyncio
async def test_on_request_can_return_content_only(app, client):

    @app.listen('request')
    async def on_request(request, response):
        assert request is not None
        assert request.path == '/default/mylayer/0/0/0.pbf'
        response.body = b'on_request'
        return True  # Shortcut request processing pipeline.

    resp = await client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status == HTTPStatus.OK
    assert resp.body == b'on_request'


@pytest.mark.asyncio
async def test_on_request_can_return_tuple(app, client):

    @app.listen('request')
    async def on_request(request, response):
        response.status = 302
        response.headers['Location'] = 'http://somewhere-else.org'
        return True  # Shortcut request processing pipeline.

    resp = await client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status == HTTPStatus.FOUND
    assert resp.headers['Location'] == 'http://somewhere-else.org'


@pytest.mark.asyncio
async def test_on_response_can_override_response_body(app, client, fetchall):

    @app.listen('response')
    async def on_response(request, response):
        response.body = b'on_response'

    fetchall([])

    resp = await client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status == HTTPStatus.OK
    assert resp.body == b'on_response'


@pytest.mark.asyncio
async def test_on_response_can_override_headers(app, client, fetchall):

    @app.listen('response')
    async def on_response(request, response, **kwargs):
        response.headers['Custom'] = 'OK'

    fetchall([])

    resp = await client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status == HTTPStatus.OK
    assert resp.headers['Custom'] == 'OK'


@pytest.mark.asyncio
async def test_cors_add_cors_headers(client, fetchall):
    fetchall([])
    resp = await client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status == HTTPStatus.OK
    assert resp.headers['Access-Control-Allow-Origin'] == '*'


@pytest.mark.asyncio
async def test_cors_can_be_changed_in_config(app, client, fetchall, config):
    config.CORS = 'http://mydomain.org'
    await app.startup()
    fetchall([])
    resp = await client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status == HTTPStatus.OK
    assert resp.headers['Access-Control-Allow-Origin'] == 'http://mydomain.org'


@pytest.mark.asyncio
async def test_cors_can_be_cancelled_in_config(app, client, fetchall, config):
    # cors has already been registered during app startup when loaded as
    # fixture. Reset this.
    app.hooks['response'] = []
    config.CORS = False
    config.LOADED = False
    await app.startup()
    fetchall([])
    resp = await client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status == HTTPStatus.OK
    assert 'Access-Control-Allow-Origin' not in resp.headers


@pytest.mark.asyncio
async def test_cache_add_cache_control_headers(client, fetchall):
    fetchall([])
    resp = await client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status == HTTPStatus.OK
    print(resp)
    assert resp.headers['Cache-Control'] == 'public,max-age=3600'


@pytest.mark.asyncio
async def test_max_age_can_be_changed_in_config(app, client, fetchall, config):
    config.MAX_AGE = 86400
    await app.startup()
    fetchall([])
    resp = await client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status == HTTPStatus.OK
    assert resp.headers['Cache-Control'] == 'public,max-age=86400'


@pytest.mark.asyncio
async def test_cache_can_be_cancelled_in_config(app, client, fetchall, config):
    # cors has already been registered during app startup when loaded as
    # fixture. Reset this.
    app.hooks['response'] = []
    config.MAX_AGE = False
    config.LOADED = False
    await app.startup()
    fetchall([])
    resp = await client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status == HTTPStatus.OK
    assert 'Cache-Control' not in resp.headers
