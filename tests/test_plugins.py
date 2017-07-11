import pytest

from utilery.core import app


@app.listen('before_load')
async def on_before_load(config):
    config.BEFORE_LOAD = True


@app.listen('load')
async def on_load(config, recipes):
    assert config.BEFORE_LOAD
    config.LOAD = True


def test_on_before_load(req, config):
    assert config.BEFORE_LOAD


def test_on_load(req, config):
    assert config.LOAD


@pytest.mark.asyncio
async def test_on_request_can_return_content_only(app, req):

    @app.listen('request')
    async def on_request(request):
        assert request is not None
        assert request.path == '/default/mylayer/0/0/0/pbf'
        return b'on_request'

    resp = await req('/default/mylayer/0/0/0/pbf')
    assert resp.status == b'200 OK'
    assert resp.body == b'on_request'


@pytest.mark.asyncio
async def test_on_request_can_return_tuple(app, req):

    @app.listen('request')
    async def on_request(request):
        return '', 302, {'Location': 'http://somewhere-else.org'}

    resp = await req('/default/mylayer/0/0/0/pbf')
    assert resp.status == b'302 Found'
    assert resp.headers['Location'] == 'http://somewhere-else.org'


@pytest.mark.asyncio
async def test_on_response_can_override_response_body(app, req, fetchall):

    @app.listen('response')
    async def on_response(response, request):
        return b'on_response'

    fetchall([])

    resp = await req('/default/mylayer/0/0/0/pbf')
    assert resp.status == b'200 OK'
    assert resp.body == b'on_response'


@pytest.mark.asyncio
async def test_on_response_can_override_response_headers(app, req, fetchall):

    @app.listen('response')
    async def on_response(response, request, **kwargs):
        response.headers['Custom'] = 'OK'

    fetchall([])

    resp = await req('/default/mylayer/0/0/0/pbf')
    assert resp.status == b'200 OK'
    assert resp.headers['Custom'] == 'OK'


@pytest.mark.asyncio
async def test_cors_add_cors_headers(req, fetchall):
    fetchall([])
    resp = await req('/default/mylayer/0/0/0/pbf')
    assert resp.status == b'200 OK'
    assert resp.headers['Access-Control-Allow-Origin'] == '*'


@pytest.mark.asyncio
async def test_cors_can_be_changed_in_config(app, req, fetchall, config):
    config.CORS = 'http://mydomain.org'
    await app.startup()
    fetchall([])
    resp = await req('/default/mylayer/0/0/0/pbf')
    assert resp.status == b'200 OK'
    assert resp.headers['Access-Control-Allow-Origin'] == 'http://mydomain.org'


@pytest.mark.asyncio
async def test_cors_can_be_cancelled_in_config(app, req, fetchall, config):
    # cors has already been registered during app startup when loaded as
    # fixture. Reset this.
    app.hooks['response'] = []
    config.CORS = False
    config.LOADED = False
    await app.startup()
    fetchall([])
    resp = await req('/default/mylayer/0/0/0/pbf')
    assert resp.status == b'200 OK'
    assert 'Access-Control-Allow-Origin' not in resp.headers
