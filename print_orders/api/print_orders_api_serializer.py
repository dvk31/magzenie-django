from rest_framework import serializers
from .models import Print_ordersModel

class Print_ordersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Print_ordersModel
        fields = '__all__'
