from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import DigitalSetupViewSet

router = DefaultRouter()
router.register(r'digital-setup', DigitalSetupViewSet, basename='digital-setup')

urlpatterns = router.urls