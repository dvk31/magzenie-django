from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from user.models import App, SupabaseInstance
from user.managers import AppManager

User = get_user_model()

class AppManagerTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.supabase_instance = SupabaseInstance.objects.create(
            owner=self.user,
            project_ref='test_ref',
            project_id='test_id',
            db_password='test_password',
            db_user='test_db_user',
            instance_url='https://test.supabase.co',
            service_role_secret='test_secret',
            public_non_key='test_public_key'
        )

    def test_create_app_with_user(self):
        app = App.objects.create(user=self.user, name='Test App', supabase_id='test_id')
        self.assertEqual(app.user, self.user)
        self.assertEqual(app.supabase_instance, self.supabase_instance)
        self.assertEqual(app.name, 'Test App')

    # Add more test methods here