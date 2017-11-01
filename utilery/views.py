from . import config
from .core import RECIPES, app
from .models import PBF, JSON, GeoJSON


@app.route('/tilejson/mvt.json')
async def tilejson(request, response):
    base = config.TILEJSON
    base['vector_layers'] = []
    for recipe in RECIPES.values():
        for layer in recipe.layers.values():
            base['vector_layers'].append({
                "description": layer.description,
                "id": layer.id
            })
    response.json = base


@app.route('/{namespace}/{names}/{z:digit}/{x:digit}/{y:digit}.pbf')
@app.route('/{names}/{z:digit}/{x:digit}/{y:digit}.pbf')
@app.route('/{namespace}/{names}/{z:digit}/{x:digit}/{y:digit}.mvt')
@app.route('/{names}/{z:digit}/{x:digit}/{y:digit}.mvt')
async def pbf(request, response, names, z, x, y, namespace='default'):
    tile = PBF(names, z, x, y, namespace)
    await tile(response)


@app.route('/{namespace}/{names}/{z:digit}/{x:digit}/{y:digit}.json')
@app.route('/{names}/{z:digit}/{x:digit}/{y:digit}.json')
async def json_(request, response, names, z, x, y, namespace='default'):
    tile = JSON(names, z, x, y, namespace)
    await tile(response)


@app.route('/{namespace}/{names}/{z:digit}/{x:digit}/{y:digit}.geojson')
@app.route('/{names}/{z:digit}/{x:digit}/{y:digit}.geojson')
async def geojson(request, response, names, z, x, y, namespace='default'):
    tile = GeoJSON(names, z, x, y, namespace)
    await tile(response)
