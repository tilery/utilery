import pytest

from utilery.core import Response


def test_on_before_load(config):
    # See TestPlugin in conftest.py
    assert config.BEFORE_LOAD


def test_on_load(config):
    # See TestPlugin in conftest.py
    assert config.LOAD


@pytest.mark.asyncio
async def test_on_request_can_return_response(req, plugins):
    class Plugin(object):

        def on_request(self, request):
            assert request is not None
            assert request.path == '/default/mylayer/0/0/0.pbf'
            return Response(b'on_request')

    plugins(Plugin())

    resp = await req('/default/mylayer/0/0/0.pbf')
    assert resp.status == b'200 OK'
    assert resp.body == b'on_request'


@pytest.mark.asyncio
async def test_on_request_can_return_tuple(req, plugins):
    class Plugin(object):

        def on_request(self, request):
            return '', 302, {'Location': 'http://somewhere-else.org'}

    plugins(Plugin())

    resp = await req('/default/mylayer/0/0/0.pbf')
    assert resp.status == b'302 Found'
    assert resp.headers['Location'] == 'http://somewhere-else.org'


@pytest.mark.asyncio
async def test_on_response_can_override_response_body(req, plugins, fetchall):
    class Plugin(object):

        def on_response(self, response, request, **kwargs):
            return Response(b'on_response')

    plugins(Plugin())
    fetchall([])

    resp = await req('/default/mylayer/0/0/0.pbf')
    assert resp.status == b'200 OK'
    assert resp.body == b'on_response'


@pytest.mark.asyncio
async def test_on_response_can_override_response_headers(req, plugins, fetchall):
    class Plugin(object):

        def on_response(self, response, request, **kwargs):
            response.headers['Custom'] = 'OK'

    plugins(Plugin())
    fetchall([])

    resp = await req('/default/mylayer/0/0/0.pbf')
    assert resp.status == b'200 OK'
    assert resp.headers['Custom'] == 'OK'


@pytest.mark.asyncio
async def test_cors_add_cors_headers(req, fetchall):
    fetchall([])
    resp = await req('/default/mylayer/0/0/0.pbf')
    assert resp.status == b'200 OK'
    assert resp.headers['Access-Control-Allow-Origin'] == '*'


@pytest.mark.asyncio
async def test_cors_can_be_changed_in_config(req, fetchall, config):
    config.CORS = 'http://mydomain.org'
    fetchall([])
    resp = await req('/default/mylayer/0/0/0.pbf')
    assert resp.status == b'200 OK'
    assert resp.headers['Access-Control-Allow-Origin'] == 'http://mydomain.org'


@pytest.mark.asyncio
async def test_cors_can_be_cancelled_in_config(req, fetchall, config):
    config.CORS = False
    fetchall([])
    resp = await req('/default/mylayer/0/0/0.pbf')
    assert resp.status == b'200 OK'
    assert 'Access-Control-Allow-Origin' not in resp.headers
