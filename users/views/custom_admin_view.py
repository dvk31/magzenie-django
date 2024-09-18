#users/views/custom_admin_view.py

from django.contrib.auth import login
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from users.auth_backends import SupabaseAuthBackend
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def custom_admin_login(request):
    logger.debug("custom_admin_login view function called")
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        backend = SupabaseAuthBackend()
        user = backend.authenticate(request, username=username, password=password)
        if user and user.is_super_admin:
            login(request, user)
            return redirect(reverse('admin:index'))
        else:
            # Redirect to a custom error page or back to login with an error message
            return redirect(reverse('admin:login') + '?error=access_denied')
    return redirect(reverse('admin:login'))