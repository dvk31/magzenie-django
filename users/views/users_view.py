from django.shortcuts import render
from .models import UsersModel

class UsersView:
    def get(self, request):
        users_objects = UsersModel.objects.all()
        return render(request, 'users/users.html', {'users_objects': users_objects})
