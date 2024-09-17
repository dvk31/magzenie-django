from rest_framework import serializers
from .models import MagazinesModel

class MagazinesSerializer(serializers.ModelSerializer):
    class Meta:
        model = MagazinesModel
        fields = '__all__'
