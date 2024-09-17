from rest_framework import serializers
from .models import MediaModel

class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaModel
        fields = '__all__'
