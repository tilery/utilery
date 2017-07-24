DATABASES = {
    'default': {
        'database': 'osm',
    }
}
RECIPES = []
TILEJSON = {
    'tilejson': '2.1.0',
    'name': 'utilery',
    'description': 'A lite vector tile server',
    'scheme': 'xyz',
    'format': 'pbf',
    'tiles': [
        'http://vector.myserver.org/all/{z}/{x}/{y}.pbf'
    ],
}
DEBUG = False
SRID = 900913
SCALE = 1
BUFFER = 0
CLIP = False
CORS = '*'
MAX_AGE = 3600
