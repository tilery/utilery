from utilery.core import application
from utilery import views  # noqa Load views to make them register.

try:
    application.serve()
except KeyboardInterrupt:
    print('Bye!')
