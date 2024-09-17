from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import (
    NotificationsResponseSerializer,
    MarkNotificationReadResponseSerializer,
    UpdateNotificationPreferencesRequestSerializer,
    UpdateNotificationPreferencesResponseSerializer
)
from .models import Notification, NotificationPreferences

class NotificationViewSet(viewsets.ViewSet):
    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'], url_path='notifications')
    def list_notifications(self, request):
        notifications = Notification.objects.filter(user=request.user)
        serializer = NotificationSerializer(notifications, many=True)
        return Response({
            "success": True,
            "notifications": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='notifications/(?P<notification_id>[^/.]+)/read')
    def mark_as_read(self, request, notification_id=None):
        try:
            notification = Notification.objects.get(notification_id=notification_id, user=request.user)
            notification.read = True
            notification.save()
            return Response({
                "success": True,
                "message": "Notification marked as read."
            }, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response({"success": False, "error": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['put'], url_path='notifications/preferences')
    def update_preferences(self, request):
        serializer = UpdateNotificationPreferencesRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        preferences, created = NotificationPreferences.objects.get_or_create(user=request.user)
        email_prefs = serializer.validated_data.get('email_notifications', {})
        sms_prefs = serializer.validated_data.get('sms_notifications', {})
        preferences.email_notifications = email_prefs
        preferences.sms_notifications = sms_prefs
        preferences.save()
        return Response({
            "success": True,
            "message": "Notification preferences updated."
        }, status=status.HTTP_200_OK)