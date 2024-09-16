from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from user.models import App, SupabaseInstance, AppManager
import uuid

User = get_user_model()



class AppManagerTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='12345',
            email='testuser@example.com'
        )
        self.supabase_instance = SupabaseInstance.objects.create(
            id=uuid.uuid4(),  # This will generate a new UUID for each test run
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
        self.assertEqual(app.supabase_instance.id, self.supabase_instance.id)  # Compare IDs
        self.assertEqual(app.name, 'Test App')