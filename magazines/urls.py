from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    MagazineViewSet,
    TemplateViewSet,
    AIProcessViewSet,
    PageViewSet,
    QRCodeViewSet,
    CTAViewSet
)

router = DefaultRouter()
router.register(r'magazines', MagazineViewSet, basename='magazines')
router.register(r'templates', TemplateViewSet, basename='templates')
router.register(r'ai-processes', AIProcessViewSet, basename='ai-processes')
router.register(r'pages', PageViewSet, basename='pages')
router.register(r'qr-codes', QRCodeViewSet, basename='qr-codes')
router.register(r'ctas', CTAViewSet, basename='ctas')

urlpatterns = router.urls