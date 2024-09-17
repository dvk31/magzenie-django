from rest_framework import serializers

class NotificationSerializer(serializers.Serializer):
    notification_id = serializers.CharField()
    type = serializers.ChoiceField(choices=["Message", "Alert"])
    content = serializers.CharField()
    timestamp = serializers.DateTimeField()
    read = serializers.BooleanField()

class NotificationsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    notifications = NotificationSerializer(many=True)

class MarkNotificationReadResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()

class UpdateNotificationPreferencesRequestSerializer(serializers.Serializer):
    email_notifications = serializers.DictField(child=serializers.BooleanField())
    sms_notifications = serializers.DictField(child=serializers.BooleanField())

class UpdateNotificationPreferencesResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()