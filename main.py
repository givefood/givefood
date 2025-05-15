import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'givefood.settings')

from givefood.wsgi import application
app = application
