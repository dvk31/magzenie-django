from rest_framework import serializers
from .models import AnalyticsModel

class AnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsModel
        fields = '__all__'
