from rest_framework import serializers

class MediaUploadResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    media_id = serializers.CharField()
    media_url = serializers.URLField()
    message = serializers.CharField()