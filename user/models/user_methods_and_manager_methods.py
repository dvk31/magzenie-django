#models/user_methods_and_manager_methods.py

import uuid
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string
from .user_roles import Role

# Manager methods
class UserManagerMethods:
    def generate_unique_username(self):
        while True:
            unique_username = str(uuid.uuid4())[:8]
            if not self.model.objects.filter(username=unique_username).exists():
                return unique_username

    def get_by_natural_key(self, username):
        return self.get(**{self.model.USERNAME_FIELD: username})

    def is_username_available(self, username):
        return not self.model.objects.filter(username=username).exists()




    @transaction.atomic
    def create_user(self, username, email=None, phone_number=None, password=None, **extra_fields):
        if not username:
            raise ValueError("Username must be set")
        
        if not self.is_username_available(username):
            raise ValueError("This username is already taken")

        if not (email or phone_number):
            raise ValueError("Either Email or Phone number must be set")

        email = self.normalize_email(email) if email else None
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        # Extract roles from extra_fields if present
        roles = extra_fields.pop('roles', None)

        user = self.model(username=username, email=email, phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)

        # Set the roles after user is saved
        if roles:
            user.roles = roles
            user.save()

        return user

    @transaction.atomic
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if not password:
            raise ValueError("Superusers must have a password.")
        if email is None:
            raise ValueError("Superusers must have an email.")

        # Get or create the admin role
        admin_role, _ = Role.objects.get_or_create(name="Admin")
        extra_fields["roles"] = admin_role

        return self.create_user(username=username, email=email, password=password, **extra_fields)

# User methods
class UserMethods:
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_short_name(self):
        return self.first_name

    def get_natural_key(self):
        return (self.username,)

    def clean(self):
        if self.email and self.phone_number:
            raise ValidationError("Either Email or Phone number must be set, not both")
        if not self.email and not self.phone_number:
            raise ValidationError("Either Email or Phone number must be set")
        if self.email and not self.is_email_available(self.email):
            raise ValidationError("This email is already taken")
        if self.phone_number and not self.is_phone_number_available(self.phone_number):
            raise ValidationError("This phone number is already taken")
        if self.role == "AGENT_CREATOR" and not hasattr(self, 'agent_creator_profile'):
            raise ValidationError("Agent Creators must have an Agent Creator Profile")

    def is_email_available(self, email):
        return not self.__class__.objects.filter(email=email).exclude(pk=self.pk).exists()

    def is_phone_number_available(self, phone_number):
        return not self.__class__.objects.filter(phone_number=phone_number).exclude(pk=self.pk).exists()

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.__class__.objects.generate_unique_username()
        self.clean()
        super().save(*args, **kwargs)

    @classmethod
    def is_username_available(cls, username):
        return cls.objects.is_username_available(username)

    @classmethod
    def update_or_create_from_supabase(cls, supabase_data):
        defaults = {
            'email': supabase_data.get('email'),
            'phone_number': supabase_data.get('phone'),
            'username': supabase_data.get('username') or cls.objects.generate_unique_username(),
            'is_active': supabase_data.get('confirmed_at') is not None,
            'last_sign_in_at': supabase_data.get('last_sign_in_at'),
            'confirmed_at': supabase_data.get('confirmed_at'),
        }
        user, created = cls.objects.update_or_create(
            supabase_uid=supabase_data['id'],
            defaults=defaults
        )
        return user, created

    def get_profile(self):
        # Implement this method based on your specific logic
        pass

    def get_effective_tone(self):
        if self.preferred_ai_tone == 'custom' and self.custom_ai_tone:
            return self.custom_ai_tone
        return self.preferred_ai_tone