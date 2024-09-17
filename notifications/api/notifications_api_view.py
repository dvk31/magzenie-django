from rest_framework import generics
from .models import NotificationsModel
from .notifications_api_serializer import NotificationsSerializer

class NotificationsAPIView(generics.ListCreateAPIView):
    queryset = NotificationsModel.objects.all()
    serializer_class = NotificationsSerializer
