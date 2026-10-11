import os
from django.core.wsgi import get_wsgi_application
from workers import wsgi

# Configure Django settings module for Cloudflare Worker
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SRCEM_CMS.settings")

# Initialize Django WSGI application
app = get_wsgi_application()

# Cloudflare Worker WSGI entrypoint
Default = wsgi.entrypoint(app)
