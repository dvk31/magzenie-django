from rest_framework import serializers
from .models import NotificationsModel

class NotificationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationsModel
        fields = '__all__'
