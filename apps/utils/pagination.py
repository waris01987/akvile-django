"""
pagination.py
Dedicated for a global CustomPagination class, which allows the response data to be paginated or to return the full
response list.
"""
import math

from rest_framework import pagination
from rest_framework.response import Response


class CustomPagination(pagination.LimitOffsetPagination):
    """
    If request is sent to ListView with url parameter ?all=true - response is returned not paginated.
    This was done to not duplicate ListViews for paginated or not paginated responses
    """

    NOT_PAGINATED_KEYWORD = "all"
    NOT_PAGINATED_VALUE = "true"

    def paginate_queryset(self, queryset, request, view=None):
        not_paginated = request.query_params.get(self.NOT_PAGINATED_KEYWORD)
        if not_paginated == self.NOT_PAGINATED_VALUE:
            self.request = request
            return list(queryset)
        return super(CustomPagination, self).paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        not_paginated = self.request.query_params.get(self.NOT_PAGINATED_KEYWORD)
        if not_paginated == self.NOT_PAGINATED_VALUE:
            return Response(data)
        return Response(
            {
                "count": self.count,
                "limit": self.limit,
                "offset": self.offset,
                "totalPages": math.ceil(self.count / self.limit),
                "currentPage": int(self.offset / self.limit),
                "results": data,
            }
        )
