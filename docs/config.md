# Utilery configuration


## Examples 

Looking at examples is often the best way to learn, so here are some:

- [https://github.com/etalab/utilery-osm-recipe/blob/master/utilery.yml](https://github.com/etalab/utilery-osm-recipe/blob/master/utilery.yml)
- [https://github.com/etalab/utilery-recipe-jurpol/blob/master/jurpol.yml](https://github.com/etalab/utilery-recipe-jurpol/blob/master/jurpol.yml)
- [https://github.com/etalab/utilery-recipe-ban/blob/master/ban.yml](https://github.com/etalab/utilery-recipe-ban/blob/master/ban.yml)


## Overview

You'll need, at minimum, two configuration files: one [python configuration file](#python-configuration),
and one [YAML file](#recipes).

The [python configuration](#python-configuration) file describes how Utilery should deal with the current
environment, so basically you'll set on this file the [database](#databases-dict-required)
crendentials and the paths of the YAML recipe(s).

A [recipe](#recipes) is a YAML file that describres how to request data to PostgreSQL; you'll have at least one,
but you can have has many as you want.


## Python configuration

This is a normal python file. You need to set a environment variable so that Utilery knows where to look
for it:

    export UTILERY_SETTINGS=/home/tile/local.py


#### DATABASES (dict) - *required*

    DATABASES = {
        "default": "dbname=utilery user=osm password=osm host=localhost"
    }

This dictionnary need to contain all the database credentials that will be referred to by the recipes.
Usually it will have one `default` key. Values are on the [LibPQ connection string format](http://www.postgresql.org/docs/current/static/libpq-connect.html#LIBPQ-CONNSTRING).


#### PLUGINS (list)

    PLUGINS = ['path.to.MyPlugin']

It's a list of paths to optional [plugins](plugins.md).


#### RECIPES (list) - *required*

    RECIPES = ['/home/tile/utilery-osm-recipe/utilery.yml']

It's a list of paths to recipes.


#### TILEJSON (dict)

    TILEJSON = {
        "tilejson": "2.1.0",
        "name": "utilery",
        "description": "A lite vector tile server",
        "scheme": "xyz",
        "format": "pbf",
        "tiles": [
            "http://vector.myserver.org/all/{z}/{x}/{y}.pbf"
        ],
    }

Default dict to use when serving the `/tilejson/` endpoint.


## Recipes

Each recipe is a single YAML file.

### **Inheritable keys**

Those keys can be set at the first level of the YAML file, or at the layer level
or at the query level.

##### buffer (integer) — *optional* — default: 0
Optional buffer (in pixels) to use when querying data.

##### clip (boolean) — *optional* — default: false
Weither to clip or not the data to the tile bbox.

##### dbname (string) — *optional* — default: "default"
Name of the database to use. This name *must* be referenced in the `DATABASES` key
of the python configuration.

##### srid (integer) — *optional* — default: 900913
SRID to use.

### **First level keys**

##### layers (sequence) - *required*
A sequence of [layers](#layer-keys) mappings.

##### name (string) — *optional* — default: "default"
**Required** when you have more than one recipe.

### **Layer keys**
The keys to use in each layer entry.

##### name (string) — *required*
The name of the layer. This is the name to be used when requesting for only one layer
in the API endpoints.

##### queries (sequence) - *required*
A sequence of [sequences](#query-keys) mappings.

### **Query keys**

##### maxzoom (integer) — *optional* — default: 0
Maximum zoom this query should be run at.

##### minzoom (integer) — *optional* — default: 0
Minimum zoom this query should be run at.

##### sql (string) — *required*
The actual sql to be run for this query. Must expose the geometry column as `way`.
Available variables: `!bbox!`, `!zoom!`, `!pixel_width!`.
