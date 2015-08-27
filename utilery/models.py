class Recipe(dict):

    DEFAULTS = {
        "srid": 900913,
        "scale": 1,
        "buffer": 0,
        "clip": False
    }

    def __init__(self, data):
        super().__init__(data)
        self.load_layers(data['layers'])

    def load_layers(self, layers):
        self.layers = {}
        for layer in layers:
            self.layers[layer['name']] = Layer(self, layer)

    def __getattr__(self, attr):
        return self.get(attr, self.DEFAULTS.get(attr))


class Layer(dict):

    def __init__(self, recipe, data):
        self.recipe = recipe
        super().__init__(data)
        self.load_queries(data['queries'])

    def load_queries(self, queries):
        self.queries = []
        for query in queries:
            self.queries.append(Query(self, query))

    def __getattr__(self, attr):
        return self.get(attr, getattr(self.recipe, attr))


class Query(dict):

    def __init__(self, layer, data):
        self.layer = layer
        super().__init__(data)

    def __getattr__(self, name):
        return self.get(name, getattr(self.layer, name))
