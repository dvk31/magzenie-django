from rest_framework import serializers
from .models import SupportModel

class SupportSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportModel
        fields = '__all__'
