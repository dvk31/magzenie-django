# hellogpt/routing.py
from django.urls import re_path
from user.consumers import UserConsumer

websocket_urlpatterns = [
    re_path(r'ws/user/$', UserConsumer.as_asgi()),
]