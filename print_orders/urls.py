from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import PrintOrderViewSet

router = DefaultRouter()
router.register(r'print-options', PrintOrderViewSet, basename='print-options')
router.register(r'print-orders', PrintOrderViewSet, basename='print-orders')

urlpatterns = router.urls