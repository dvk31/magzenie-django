from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import MediaUploadResponseSerializer
from .models import Media
from django.core.files.storage import default_storage

class MediaViewSet(viewsets.ViewSet):
    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        return [IsAuthenticated()]

    @action(detail=False, methods=['post'], url_path='media/upload')
    def upload_media(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({
                "success": False,
                "message": "No file uploaded."
            }, status=status.HTTP_400_BAD_REQUEST)
        file_name = default_storage.save(f'media/{file.name}', file)
        media_url = default_storage.url(file_name)
        media = Media.objects.create(
            user=request.user,
            file=file,
            media_url=media_url
        )
        return Response({
            "success": True,
            "media_id": media.media_id,
            "media_url": media_url,
            "message": "Media uploaded successfully."
        }, status=status.HTTP_201_CREATED)