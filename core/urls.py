from django.urls import path
from .views import CreateSupabaseInstanceView

urlpatterns = [
    path('create-supabase/', CreateSupabaseInstanceView.as_view(), name='create_supabase_instance'),
]