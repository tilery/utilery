from utilery import config


class CORS(object):

    def on_response(self, response, request):
        if config.CORS:
            response.headers["Access-Control-Allow-Origin"] = config.CORS
            response.headers["Access-Control-Allow-Headers"] = "X-Requested-With"  # noqa
