 #schemas.py

from drf_spectacular.utils import extend_schema, OpenApiExample
from .serializers import (
    UserSettingsSerializer,
    UpdateUserSettingsResponseSerializer,
    UpdateUserSettingsProfileRequestSerializer,
    ErrorResponseSerializer
)

# Define the schema for GET method
user_settings_get_schema = extend_schema(
    methods=['GET'],
    description="Retrieve the authenticated user's settings.",
    responses={
        200: UserSettingsSerializer,
        401: ErrorResponseSerializer,
        500: ErrorResponseSerializer,
    },
    examples=[
        OpenApiExample(
            'Example GET Response',
            value={
                "profile": {
                    "full_name": "John Doe",
                    "profile_picture": "http://example.com/image.jpg",
                    "email": "john.doe@example.com",
                    "is_active": True
                },
                "subscription": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "plan": {
                        "id": "223e4567-e89b-12d3-a456-426614174001",
                        "name": "Premium Plan",
                        "price": 19.99,
                        "duration_months": 1,
                        "description": "Premium features included"
                    },
                    "start_date": "2023-09-16",
                    "end_date": "2024-09-15",
                    "active": True
                },
                "payment_methods": [
                    {
                        "id": "323e4567-e89b-12d3-a456-426614174002",
                        "method_type": "credit_card",
                        "last_four_digits": "1234",
                        "expiry_date": "2025-12-31"
                    }
                ],
                "addresses": [
                    {
                        "id": "423e4567-e89b-12d3-a456-426614174003",
                        "address_type": "Billing",
                        "line1": "123 Main St",
                        "line2": "Apt 4B",
                        "city": "Anytown",
                        "state": "Anystate",
                        "postal_code": "12345",
                        "country": "USA"
                    }
                ],
                "notification_preferences": {
                    "email_notifications": True,
                    "sms_notifications": False
                }
            },
            response_only=True
        ),
    ]
)

# Define the schema for PUT and PATCH methods
user_settings_put_patch_schema = extend_schema(
    methods=['PUT', 'PATCH'],
    description="Update the authenticated user's settings.",
    request=UpdateUserSettingsProfileRequestSerializer,
    responses={
        200: UpdateUserSettingsResponseSerializer,
        400: ErrorResponseSerializer,
        401: ErrorResponseSerializer,
        500: ErrorResponseSerializer,
    },
    examples=[
        OpenApiExample(
            'Example PUT Request',
            value={
                "profile": {
                    "full_name": "Johnathan Doe",
                    "profile_picture_url": "http://example.com/new_image.jpg"
                }
            },
            request_only=True
        ),
        OpenApiExample(
            'Example PATCH Request',
            value={
                "profile": {
                    "full_name": "Jane Doe"
                }
            },
            request_only=True
        ),
        OpenApiExample(
            'Example PUT/PATCH Response',
            value={
                "success": True,
                "message": "Settings updated successfully."
            },
            response_only=True
        )
    ]
)