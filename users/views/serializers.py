#users/views/serializers.py



from rest_framework import serializers
from django.contrib.auth import get_user_model
from users.models import (
    UserProfile,
   
   
)

from notifications.models.notifications_model import (NotificationPreferences, Notification)
from payments.models import (
    Payment,
    PromoCode,
    SubscriptionPlan,
    Subscription,
    Address,
    PaymentMethod
)

User = get_user_model()

class RegistrationRequestSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    terms_accepted = serializers.BooleanField()

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        if not data['terms_accepted']:
            raise serializers.ValidationError("You must accept the terms and conditions.")
        return data

class RegistrationResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    user_id = serializers.IntegerField()
    message = serializers.CharField()

class LoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class LoginResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    user_id = serializers.IntegerField()
    token = serializers.CharField()
    message = serializers.CharField()

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmationSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("New passwords do not match.")
        return data

class LogoutResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()

class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email')
    is_active = serializers.BooleanField(source='user.is_active')

    class Meta:
        model = UserProfile
        fields = ['full_name', 'profile_picture', 'email', 'is_active']

class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['id', 'method_type', 'last_four_digits', 'expiry_date']

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'line1', 'line2', 'city', 'state', 'postal_code', 'country', 'address_type']

class NotificationPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreferences
        fields = ['email_notifications', 'sms_notifications']

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'price', 'duration_months', 'description']

class SubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = ['id', 'plan', 'start_date', 'end_date', 'active']
        read_only_fields = ['id', 'plan', 'start_date', 'end_date', 'active']

class UserSettingsSerializer(serializers.Serializer):
    profile = UserProfileSerializer()
    subscription = SubscriptionSerializer()
    payment_methods = PaymentMethodSerializer(many=True)
    addresses = AddressSerializer(many=True)
    notification_preferences = NotificationPreferencesSerializer()

class UpdateUserSettingsProfileRequestSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=False)
    profile_picture_url = serializers.URLField(required=False)

    class Meta:
        partial = True

class UpdateUserSettingsPasswordRequestSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("New passwords do not match.")
        return data

class AddPaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['method_type', 'last_four_digits', 'expiry_date']

class AddAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['line1', 'line2', 'city', 'state', 'postal_code', 'country', 'address_type']

class UpdateUserSettingsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    updated_fields = serializers.ListField(child=serializers.CharField(), required=False)

class ErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=False)
    message = serializers.CharField()
    error_code = serializers.CharField(required=False)
    errors = serializers.DictField(required=False, allow_empty=True)


class ErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=False)
    message = serializers.CharField()
    errors = serializers.DictField(required=False, allow_empty=True)

    def to_representation(self, instance):
        """
        Customize the representation to include only the provided fields.
        This ensures that optional fields like 'errors' are included only when present.
        """
        ret = {}
        if 'success' in instance:
            ret['success'] = instance['success']
        if 'message' in instance:
            ret['message'] = instance['message']
        if 'errors' in instance:
            ret['errors'] = instance['errors']
        return ret


