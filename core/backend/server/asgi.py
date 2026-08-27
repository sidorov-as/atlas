from django.core.asgi import get_asgi_application

from server.apps.plugins.startup import bootstrap

bootstrap()

application = get_asgi_application()
