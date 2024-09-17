from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import SupportViewSet

router = DefaultRouter()
router.register(r'support', SupportViewSet, basename='support')

urlpatterns = router.urls