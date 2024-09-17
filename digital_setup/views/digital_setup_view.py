from django.shortcuts import render
from .models import Digital_setupModel

class Digital_setupView:
    def get(self, request):
        digital_setup_objects = Digital_setupModel.objects.all()
        return render(request, 'digital_setup/digital_setup.html', {'digital_setup_objects': digital_setup_objects})
