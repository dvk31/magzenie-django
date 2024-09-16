# core/middleware/swaggertoken.py
class SwaggerTokenPrefixMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the Authorization header is present and lacks the "Bearer" prefix
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header and not auth_header.startswith("Bearer"):
            # Prepend "Bearer" to the authorization header if necessary
            # Or leave it as is if your system uses a different prefix or no prefix
            # Uncomment the following line if you want to prepend "Bearer" to the authorization header
            # request.META['HTTP_AUTHORIZATION'] = "Bearer " + auth_header
            pass  # Add this line if you want to do nothing and avoid the IndentationError

        response = self.get_response(request)
        return response