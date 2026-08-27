from django.core.wsgi import get_wsgi_application

from server.apps.plugins.startup import bootstrap

bootstrap()

application = get_wsgi_application()
