from django.shortcuts import render
from .models import NotificationsModel

class NotificationsView:
    def get(self, request):
        notifications_objects = NotificationsModel.objects.all()
        return render(request, 'notifications/notifications.html', {'notifications_objects': notifications_objects})
