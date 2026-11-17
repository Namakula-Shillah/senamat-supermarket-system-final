
from django.utils.cache import add_never_cache_headers


class NoStoreForAuthenticatedHTMLMiddleware:
    """
    Prevent browsers and intermediary caches from
    storing authenticated dashboard HTML pages.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        user = getattr(request, "user", None)

        if (
            request.method == "GET"
            and user is not None
            and user.is_authenticated
            and response.get("Content-Type", "").startswith("text/html")
        ):
            add_never_cache_headers(response)

        return response
