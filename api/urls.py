from django.urls import path, include
from .dynamic_api import dynamic_api_urlpatterns
from .views import LoginView, RefreshTokenView, LogoutView, SignupView

urlpatterns = [
    # Your existing URL patterns...
    path('login/', LoginView.as_view(), name='login'),
    path('refresh-token/', RefreshTokenView.as_view(), name='refresh_token'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('', include(dynamic_api_urlpatterns)),
]
