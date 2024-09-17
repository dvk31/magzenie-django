from django.shortcuts import render
from .models import MagazinesModel

class MagazinesView:
    def get(self, request):
        magazines_objects = MagazinesModel.objects.all()
        return render(request, 'magazines/magazines.html', {'magazines_objects': magazines_objects})
