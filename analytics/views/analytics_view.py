from django.shortcuts import render
from .models import AnalyticsModel

class AnalyticsView:
    def get(self, request):
        analytics_objects = AnalyticsModel.objects.all()
        return render(request, 'analytics/analytics.html', {'analytics_objects': analytics_objects})
