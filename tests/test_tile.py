import pytest

from utilery.models import PBF


pytestmark = pytest.mark.asyncio


async def test_simple_request(req, fetchall):

    def check_query(query, *args, **kwargs):
        assert 'SELECT' in query
        assert 'ST_Intersection' not in query
        assert 'ST_Expand' not in query

    fetchall([], check_query)

    assert await PBF(names='all', z=0, x=0, y=0)()


async def test_does_not_request_if_lower_than_minzoom(req, fetchall, layer):

    layer['queries'].append({
        'sql': 'SELECT geometry AS way, type, name FROM youdontwantme',
        'minzoom': 9
    })

    def check_query(query, *args, **kwargs):
        assert "youdontwantme" not in query

    fetchall([], check_query)

    assert await PBF(names='all', z=0, x=0, y=0)()


async def test_does_not_request_if_higher_than_maxzoom(req, fetchall, layer):

    layer['queries'].append({
        'sql': 'SELECT geometry AS way, type, name FROM youdontwantme',
        'maxzoom': 1
    })

    def check_query(query, *args, **kwargs):
        assert "youdontwantme" not in query

    fetchall([], check_query)

    assert await PBF(names='all', z=2, x=0, y=0)()


async def test_can_change_srid(req, fetchall, layer):

    layer['srid'] = 4326

    def check_query(query, *args, **kwargs):
        assert 'st_transform' in query.lower()
        assert '4326' in query.lower()

    fetchall([], check_query)

    assert await PBF(names='all', z=0, x=0, y=0)()


async def test_should_not_transform_900913_projection(req, fetchall, layer):

    layer['srid'] = 900913

    def check_query(query, *args, **kwargs):
        assert 'st_transform' not in query.lower()
        assert '900913' not in query

    fetchall([], check_query)

    assert await PBF(names='all', z=0, x=0, y=0)()


async def test_should_not_transform_3857_projection(req, fetchall, layer):

    layer['srid'] = 3857

    def check_query(query, *args, **kwargs):
        assert 'st_transform' not in query.lower()

    fetchall([], check_query)

    assert await PBF(names='all', z=0, x=0, y=0)()


async def test_clip_when_asked(req, fetchall, layer):

    layer['clip'] = True

    def check_query(query, *args, **kwargs):
        assert "ST_Intersection" in query

    fetchall([], check_query)

    assert await PBF(names='all', z=0, x=0, y=0)()


async def test_add_buffer_when_asked(req, fetchall, layer):

    layer['buffer'] = 128

    def check_query(query, *args, **kwargs):
        assert "ST_Expand" in query

    fetchall([], check_query)

    assert await PBF(names='all', z=0, x=0, y=0)()


async def test_no_buffer_by_default(req, fetchall, layer):

    layer['buffer'] = 0

    def check_query(query, *args, **kwargs):
        assert "ST_Expand" not in query

    fetchall([], check_query)

    assert await PBF(names='all', z=0, x=0, y=0)()


async def test_filter_valid_when_asked(req, fetchall, layer):

    layer['is_valid'] = True

    def check_query(query, *args, **kwargs):
        assert "ST_IsValid" in query

    fetchall([], check_query)

    assert await PBF(names='all', z=0, x=0, y=0)()


async def test_do_not_filter_valid_by_default(req, fetchall, layer):

    layer['is_valid'] = False

    def check_query(query, *args, **kwargs):
        assert "ST_IsValid" not in query

    fetchall([], check_query)

    assert await PBF(names='all', z=0, x=0, y=0)()
