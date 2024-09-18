import graphene
   from graphene_django import DjangoObjectType
   from users.models import User, UserProfile
   from graphql_jwt.decorators import login_required
   from supabase import create_client
   from django.conf import settings

   supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

   class UserType(DjangoObjectType):
       class Meta:
           model = User
           fields = ("id", "email", "username")

   class UserProfileType(DjangoObjectType):
       class Meta:
           model = UserProfile
           fields = ("id", "full_name", "profile_picture")

   class Query(graphene.ObjectType):
       users = graphene.List(UserType)
       user = graphene.Field(UserType, id=graphene.ID(required=True))
       me = graphene.Field(UserType)

       @login_required
       def resolve_users(self, info):
           return User.objects.all()

       @login_required
       def resolve_user(self, info, id):
           return User.objects.get(pk=id)

       @login_required
       def resolve_me(self, info):
           return info.context.user

   class CreateUser(graphene.Mutation):
       class Arguments:
           username = graphene.String(required=True)
           email = graphene.String(required=True)
           password = graphene.String(required=True)
           full_name = graphene.String(required=True)

       user = graphene.Field(UserType)

       def mutate(self, info, username, email, password, full_name):
           # Create user in Supabase
           supabase_user = supabase.auth.sign_up({
               "email": email,
               "password": password,
           })

           # Create user in Django
           user = User.objects.create_user(
               username=username,
               email=email,
               password=password,
               supabase_user_id=supabase_user.user.id
           )

           # Create user profile
           UserProfile.objects.create(user=user, full_name=full_name)

           return CreateUser(user=user)

   class Mutation(graphene.ObjectType):
       create_user = CreateUser.Field()

   schema = graphene.Schema(query=Query, mutation=Mutation)