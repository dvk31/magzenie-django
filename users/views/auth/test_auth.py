# users/views.py
import logging
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.contrib.auth import get_backends  # Add this import

logger = logging.getLogger(__name__)

def test_auth(request):
    username = request.GET.get('username')
    password = request.GET.get('password')
    logger.debug(f"Attempting to authenticate user: {username}")
    user = authenticate(request, username=username, password=password)
    logger.debug(f"Authentication result: {'Success' if user else 'Failure'}")
    if user is None:
        logger.debug("Authentication backends used:")
        for backend in get_backends():
            logger.debug(f" - {backend.__class__.__name__}")
    return JsonResponse({
        'authenticated': user is not None,
        'username': username,
        'backends_checked': [backend.__class__.__name__ for backend in get_backends()]
    })