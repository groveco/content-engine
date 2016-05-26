import os

DEBUG = os.environ.get('DEBUG', True)
SECRET_KEY = os.environ.get('FLASK_SECRET', '1234567890')
API_TOKEN = os.environ.get('API_TOKEN', 'FOOBAR1')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
