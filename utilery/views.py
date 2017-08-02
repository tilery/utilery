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


# TODO use .ext instead of /ext
# see https://github.com/nitely/kua/issues/5
@app.route('/:namespace/:names/:z/:x/:y/pbf')
@app.route('/:names/:z/:x/:y/pbf')
@app.route('/:namespace/:names/:z/:x/:y/mvt')
@app.route('/:names/:z/:x/:y/mvt')
async def pbf(request, response, names, z, x, y, namespace='default'):
    tile = PBF(names, z, x, y, namespace)
    await tile(response)


@app.route('/:namespace/:names/:z/:x/:y/json')
@app.route('/:names/:z/:x/:y/json')
async def json_(request, response, names, z, x, y, namespace='default'):
    tile = JSON(names, z, x, y, namespace)
    await tile(response)


@app.route('/:namespace/:names/:z/:x/:y/geojson')
@app.route('/:names/:z/:x/:y/geojson')
async def geojson(request, response, names, z, x, y, namespace='default'):
    tile = GeoJSON(names, z, x, y, namespace)
    await tile(response)
