from rest_framework import serializers
from .models import UsersModel

class UsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsersModel
        fields = '__all__'
