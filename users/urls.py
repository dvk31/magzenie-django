# users/urls.py
# users/urls.py

from django.urls import path
from users.views.custom_admin_view import custom_admin_login
from users.views.auth.test_auth import test_auth

print("Users URLs are being loaded!")

urlpatterns = [
    path('admin/login/',custom_admin_login, name='custom_admin_login'),
    path('test-auth/', test_auth, name='test_auth')
]

