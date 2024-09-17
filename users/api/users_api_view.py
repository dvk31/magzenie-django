from rest_framework import generics
from .models import UsersModel
from .users_api_serializer import UsersSerializer

class UsersAPIView(generics.ListCreateAPIView):
    queryset = UsersModel.objects.all()
    serializer_class = UsersSerializer
