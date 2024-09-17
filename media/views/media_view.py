from django.shortcuts import render
from .models import MediaModel

class MediaView:
    def get(self, request):
        media_objects = MediaModel.objects.all()
        return render(request, 'media/media.html', {'media_objects': media_objects})
