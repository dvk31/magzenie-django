from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
import yaml

# Customize the admin site
admin.site.site_header = 'Magzenie Admin Portal'
admin.site.site_title = 'Magzenie Portal'
admin.site.index_title = 'Welcome to Magzenie Admin'

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return HttpResponse("OK")

def load_yaml_with_anchors(file_path):
    class AnchorLoader(yaml.SafeLoader):
        def __init__(self, stream):
            super().__init__(stream)
            self.add_constructor('tag:yaml.org,2002:merge', type(self).construct_yaml_merge)

        def construct_yaml_merge(self, node):
            return self.construct_mapping(node)

    with open(file_path, 'r') as file:
        return yaml.load(file, Loader=AnchorLoader)

# Load the main YAML file
yaml_content = load_yaml_with_anchors('hellogpt/api_docs/api_schema.yaml')

schema_view = get_schema_view(
   openapi.Info(
      title=yaml_content['info']['title'],
      default_version=yaml_content['info']['version'],
      description=yaml_content['info'].get('description', ''),
   ),
   public=True,
   permission_classes=(AllowAny,),
   patterns=[path('api/', include('users.urls'))],
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Health Check
    path('health/', health_check, name='health_check'),

    # API Documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # API URLs
    path('', include('users.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)