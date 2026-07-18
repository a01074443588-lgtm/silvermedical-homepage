from django.shortcuts import redirect
from django.utils.cache import add_never_cache_headers, patch_vary_headers


class StaffSessionSafetyMiddleware:
    """Prevent stale admin login pages and cached staff screens."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_staff_login = request.path == "/staff/login/"
        is_authenticated_staff = (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.is_staff
        )

        if is_staff_login and is_authenticated_staff:
            response = redirect("admin:index")
        else:
            response = self.get_response(request)

        if request.path.startswith("/staff/"):
            add_never_cache_headers(response)
            patch_vary_headers(response, ("Cookie",))
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"

        return response
