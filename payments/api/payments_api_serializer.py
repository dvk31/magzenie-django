from rest_framework import serializers
from .models import PaymentsModel

class PaymentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentsModel
        fields = '__all__'
