# users/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from users.views import AuthViewSet, PasswordResetViewSet, UserSettingsViewSet

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'password-reset', PasswordResetViewSet, basename='password-reset')
router.register(r'user-settings', UserSettingsViewSet, basename='user-settings')

urlpatterns = [
    path('', include(router.urls)),
]
