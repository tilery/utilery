import os

from utilery.core import app

# Import views to make Flask know about them
import utilery.views  # noqa

app.run(debug=os.environ.get('DEBUG', True), host='0.0.0.0', port=3579)
