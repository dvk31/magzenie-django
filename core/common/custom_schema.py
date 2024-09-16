# core.common.custom_schema.py
from drf_spectacular.openapi import AutoSchema
from rest_framework.authentication import TokenAuthentication


class CustomAutoSchema(AutoSchema):
    def get_authenticators(self):
        """
        Generate a list of all authenticators used by this operation.
        """
        authenticators = super().get_authenticators()

        # Modify the token format
        for auth in authenticators:
            if isinstance(auth, TokenAuthentication):
                auth.keyword = "Bearer"  # Set 'Bearer' keyword

        return authenticators