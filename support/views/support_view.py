from django.shortcuts import render
from .models import SupportModel

class SupportView:
    def get(self, request):
        support_objects = SupportModel.objects.all()
        return render(request, 'support/support.html', {'support_objects': support_objects})
