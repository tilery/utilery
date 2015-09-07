# Utilery HTTP API

Utilery exposes a very simple HTTP API. Here are the existing endpoints.

## Endpoints

### /&lt;recipe>/&lt;names>/&lt;int:zoom>/&lt;int:x>/&lt;int:y>.(pbf|mvt)

Serves [protobuf tiles](https://github.com/mapbox/mapnik-vector-tile) for the given `recipe`, `names`,
`zoom` and `x` and `y` coordinates, where:

- `recipe` is the optional name of the recipe to target; if not set, it will default to the
  "default" recipe (which is the first loaded in the configuration).
- `names` is a `+` separated list of layers names, or the special keyword `all` that
  will consider all layers.
- `zoom`, `x`, `y` are the classic coordinates of the wanted tile, in "[web tile format](http://www.thunderforest.com/tutorials/tile-format/)"


### /&lt;recipe>/&lt;names>/&lt;int:zoom>/&lt;int:x>/&lt;int:y>.json

Same scheme than protobuf tiles, but serves them in raw json.

### /&lt;recipe>/&lt;names>/&lt;int:zoom>/&lt;int:x>/&lt;int:y>.geojson

Same scheme than protobuf tiles, but serves them as a geojson FeatureCollection. The key
`layer` is added to each Feature, given that they are all grouped in one collection.

### /tilejson/mvt.json

The [Tilejson](https://github.com/mapbox/tilejson-spec) describing the current Utilery deployment.
