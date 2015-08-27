from utilery.models import Recipe, Layer, Query


def test_basic_recipe():
    recipe = Recipe({
        "name": "myrecipe",
        "layers": [{
            "name": "mylayer",
            "queries": [{
                "sql": "SELECT * FROM table"
            }]
        }]
    })
    assert isinstance(recipe, Recipe)
    assert isinstance(recipe.layers['mylayer'], Layer)
    assert isinstance(recipe.layers['mylayer'].queries[0], Query)


def test_query_inherit_from_parents():
    recipe = Recipe({
        "name": "myrecipe",
        "srid": 3857,
        "buffer": 256,
        "layers": [{
            "name": "mylayer",
            "buffer": 128,
            "queries": [{
                "sql": "SELECT * FROM table"
            }]
        }]
    })
    query = recipe.layers['mylayer'].queries[0]
    assert query.sql == "SELECT * FROM table"
    assert query.buffer == 128
    assert query.srid == 3857
    assert query.unknown is None
