from utilery.views import app
from werkzeug.serving import run_simple


run_simple('0.0.0.0', 3579, app, use_debugger=True, use_reloader=True)
