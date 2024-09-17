from rest_framework import serializers
from .models import (
    Template,
    Magazine,
    GeneratedContent,
    Page,
    QRCode,
    CTA
)
# Assume appropriate models are defined in models.py

class CreateMagazineRequestSerializer(serializers.Serializer):
    template_id = serializers.CharField()
    magazine_title = serializers.CharField()

class CreateMagazineResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    magazine_id = serializers.CharField()
    message = serializers.CharField()

class MagazineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Magazine
        fields = ['magazine_id', 'title', 'status', 'last_modified', 'thumbnail_url']

class MagazinesResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    magazines = MagazineSerializer(many=True)

class DuplicateMagazineResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    new_magazine_id = serializers.CharField()
    message = serializers.CharField()

class SubmitAirbnbURLRequestSerializer(serializers.Serializer):
    airbnb_url = serializers.URLField(required=False)
    manual_data = serializers.JSONField(required=False)

    def validate(self, data):
        if not data.get('airbnb_url') and not data.get('manual_data'):
            raise serializers.ValidationError("Either airbnb_url or manual_data must be provided.")
        return data

class SubmitAirbnbURLResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    ai_process_id = serializers.CharField()

class StartAIContentGenerationResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    ai_process_id = serializers.CharField()

class AIContentGenerationStatusSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    status = serializers.ChoiceField(choices=["Pending", "In_Progress", "Completed", "Failed"])
    progress = serializers.IntegerField()
    estimated_time_remaining = serializers.CharField()

class GeneratedContentSerializer(serializers.Serializer):
    page_id = serializers.CharField()
    content = serializers.JSONField()
    accepted = serializers.BooleanField()

class GetGeneratedContentResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    pages = GeneratedContentSerializer(many=True)

class UpdatePageContentRequestSerializer(serializers.Serializer):
    content = serializers.JSONField()
    accepted = serializers.BooleanField()

class UpdatePageContentResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()

class AddPageRequestSerializer(serializers.Serializer):
    content = serializers.JSONField()

class AddPageResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    page_id = serializers.CharField()
    message = serializers.CharField()

class DeletePageResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()

class QRCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = QRCode
        fields = ['page_id', 'qr_code_id', 'qr_code_url', 'linked_url']

class QRCodesResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    qr_codes = QRCodeSerializer(many=True)

class CustomizeQRCodeRequestSerializer(serializers.Serializer):
    color = serializers.CharField()
    logo_url = serializers.URLField()
    linked_url = serializers.URLField()

class CustomizeQRCodeResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    qr_code_url = serializers.URLField()
    message = serializers.CharField()

class CTA_Serializer(serializers.ModelSerializer):
    class Meta:
        model = CTA
        fields = ['page_id', 'suggested_cta', 'custom_cta', 'linked_url']

class CTAsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    ctas = CTA_Serializer(many=True)

class UpdateCTADRequestSerializer(serializers.Serializer):
    custom_cta = serializers.CharField()
    linked_url = serializers.URLField()
    accept_suggestion = serializers.BooleanField()

class UpdateCTAResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()