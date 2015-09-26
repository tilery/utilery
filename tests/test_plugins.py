from werkzeug.wrappers import Response


def test_on_before_load(config):
    # See TestPlugin in conftest.py
    assert config.BEFORE_LOAD


def test_on_load(config):
    # See TestPlugin in conftest.py
    assert config.LOAD


def test_on_request_can_return_response(client, plugins):
    class Plugin(object):

        def on_request(self, endpoint, request, **kwargs):
            assert endpoint == 'pbf'
            assert request is not None
            assert request.path == '/default/mylayer/0/0/0.pbf'
            return Response('on_request')

    plugins(Plugin())

    resp = client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status_code == 200
    assert resp.data == b'on_request'


def test_on_request_can_return_tuple(client, plugins):
    class Plugin(object):

        def on_request(self, endpoint, request, **kwargs):
            return '', 302, {'Location': 'http://somewhere-else.org'}

    plugins(Plugin())

    resp = client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status_code == 302
    assert resp.headers['Location'] == 'http://somewhere-else.org'


def test_on_response_can_override_response_content(client, plugins, fetchall):
    class Plugin(object):

        def on_response(self, response, request, **kwargs):
            return Response('on_response')

    plugins(Plugin())
    fetchall([])

    resp = client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status_code == 200
    assert resp.data == b'on_response'


def test_on_response_can_override_response_headers(client, plugins, fetchall):
    class Plugin(object):

        def on_response(self, response, request, **kwargs):
            response.headers['Custom'] = 'OK'

    plugins(Plugin())
    fetchall([])

    resp = client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status_code == 200
    assert resp.headers['Custom'] == 'OK'


def test_cors_add_cors_headers(client, fetchall):
    fetchall([])
    resp = client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status_code == 200
    assert resp.headers['Access-Control-Allow-Origin'] == '*'


def test_cors_can_be_changed_in_config(client, fetchall, config):
    config.CORS = 'http://mydomain.org'
    fetchall([])
    resp = client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status_code == 200
    assert resp.headers['Access-Control-Allow-Origin'] == 'http://mydomain.org'


def test_cors_can_be_cancelled_in_config(client, fetchall, config):
    config.CORS = False
    fetchall([])
    resp = client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status_code == 200
    assert 'Access-Control-Allow-Origin' not in resp.headers
