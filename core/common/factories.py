import factory
from django.contrib.auth import get_user_model
from space.models import Space
from user.models import UsersModel

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()
    
    username = factory.Sequence(lambda n: f'user{n}')

class SpaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Space
    
    name = factory.Sequence(lambda n: f'Space {n}')
    owner = factory.SubFactory(UserFactory)