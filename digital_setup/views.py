from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import (
    DigitalSetupInstructionsResponseSerializer,
    UpdateDigitalSettingsRequestSerializer,
    UpdateDigitalSettingsResponseSerializer
)
from magazines.models import Magazine

class DigitalSetupViewSet(viewsets.ViewSet):
    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'], url_path='digital-setup/instructions')
    def get_instructions(self, request):
        instructions = "<p>Follow these steps to set up your digital magazine...</p>"
        download_links = {
            "android": "https://play.google.com/store/apps/details?id=com.magzenie.app",
            "ios": "https://apps.apple.com/app/magzenie/id123456789"
        }
        qr_codes = {
            "android": "https://example.com/qrcodes/android.png",
            "ios": "https://example.com/qrcodes/ios.png"
        }
        support_links = [
            {"title": "Setup Guide", "url": "https://example.com/support/setup-guide"}
        ]
        serializer = DigitalSetupInstructionsResponseSerializer({
            "success": True,
            "instructions": instructions,
            "download_links": download_links,
            "qr_codes": qr_codes,
            "support_links": support_links
        })
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['put'], url_path='digital-setup/settings')
    def update_settings(self, request):
        serializer = UpdateDigitalSettingsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # Update digital settings for the user
        # Assume user has a DigitalSettings model related
        digital_settings, created = DigitalSettings.objects.get_or_create(user=request.user)
        digital_settings.enable_kiosk_mode = data['enable_kiosk_mode']
        digital_settings.auto_launch_magazine = data['auto_launch_magazine']
        if data['selected_magazine_id']:
            digital_settings.selected_magazine = Magazine.objects.get(magazine_id=data['selected_magazine_id'], user=request.user)
        digital_settings.save()
        return Response({
            "success": True,
            "message": "Digital settings updated successfully."
        }, status=status.HTTP_200_OK)