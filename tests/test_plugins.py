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

    plugins.append(Plugin())

    resp = client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status_code == 200
    assert resp.data == b'on_request'


def test_on_request_can_return_tuple(client, plugins):
    class Plugin(object):

        def on_request(self, endpoint, request, **kwargs):
            return '', 302, {'Location': 'http://somewhere-else.org'}

    plugins.append(Plugin())

    resp = client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status_code == 302
    assert resp.headers['Location'] == 'http://somewhere-else.org'


def test_on_response_can_override_response_content(client, plugins, fetchall):
    class Plugin(object):

        def on_response(self, response, request, **kwargs):
            return Response('on_response')

    plugins.append(Plugin())
    fetchall([])

    resp = client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status_code == 200
    assert resp.data == b'on_response'


def test_on_response_can_override_response_headers(client, plugins, fetchall):
    class Plugin(object):

        def on_response(self, response, request, **kwargs):
            response.headers['Custom'] = 'OK'

    plugins.append(Plugin())
    fetchall([])

    resp = client.get('/default/mylayer/0/0/0.pbf')
    assert resp.status_code == 200
    assert resp.headers['Custom'] == 'OK'
