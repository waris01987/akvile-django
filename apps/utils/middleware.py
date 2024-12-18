from typing import Callable, Union

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponseForbidden
from rest_framework.response import Response


class UserAgentMiddleware:
    """We get an error when a crawler tries to crawl our site, since it's sending incorrect headers results.
    Since this happens very often, it's spamming our sentry with errors.
    """

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: WSGIRequest) -> Union[Response, HttpResponseForbidden]:
        if not request.headers.get("User-Agent"):
            return HttpResponseForbidden("Access denied.")
        return self.get_response(request)
