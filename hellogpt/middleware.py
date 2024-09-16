# middleware.py
import threading

class RequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.thread_local = threading.local()

    def __call__(self, request):
        self.thread_local.request = request
        response = self.get_response(request)
        return response