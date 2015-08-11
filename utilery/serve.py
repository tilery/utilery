import os

from utilery.core import app

app.run(debug=os.environ.get('DEBUG', True), host='0.0.0.0', port=3579)
