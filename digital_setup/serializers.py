from rest_framework import serializers

class DigitalSetupInstructionsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    instructions = serializers.CharField()
    download_links = serializers.DictField()
    qr_codes = serializers.DictField()
    support_links = serializers.ListField(child=serializers.DictField())

class UpdateDigitalSettingsRequestSerializer(serializers.Serializer):
    enable_kiosk_mode = serializers.BooleanField()
    auto_launch_magazine = serializers.BooleanField()
    selected_magazine_id = serializers.CharField()

class UpdateDigitalSettingsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()