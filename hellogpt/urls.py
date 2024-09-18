from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from api.urls import urlpatterns as users_urlpatterns
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
# Customize the admin site
schema_view = get_schema_view(
    openapi.Info(
        title="Your Project API",
        default_version='v1',
        description="Auto-generated API documentation",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@yourproject.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return HttpResponse("OK")

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Health Check
    path('health/', health_check, name='health_check'),

    path('api/', include((users_urlpatterns, 'api'), namespace='api')),
    path('swagger(<format>\.json|\.yaml)', schema_view.without_ui(cache_timeout=0), name='schema-json'),

    path('api/schema/', permission_classes([AllowAny])(SpectacularAPIView.as_view()), name='schema'),
    path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', permission_classes([AllowAny])(SpectacularRedocView.as_view(url_name='schema')), name='redoc'),

  
    path('', include('users.urls')), 
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)