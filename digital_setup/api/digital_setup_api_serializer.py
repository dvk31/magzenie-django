from rest_framework import serializers
from .models import Digital_setupModel

class Digital_setupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Digital_setupModel
        fields = '__all__'
