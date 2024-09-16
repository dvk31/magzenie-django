from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

# Customize the admin site
admin.site.site_header = 'PeeQShop Admin Portal'
admin.site.site_title = 'PeeQShop Portal'
admin.site.index_title = 'Welcome to PeeQShop Admin'

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return HttpResponse("OK")

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Health Check
    path('health/', health_check, name='health_check'),

    # API Documentation
    path('api/schema/', permission_classes([AllowAny])(SpectacularAPIView.as_view()), name='schema'),
    path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', permission_classes([AllowAny])(SpectacularRedocView.as_view(url_name='schema')), name='redoc'),

    # API Endpoints
    #path('api/v1/', include('core.urls')),
    #path('api/v1/', include('user.urls')),
 
    #path('userapp/api/v1/', include('userapp.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)