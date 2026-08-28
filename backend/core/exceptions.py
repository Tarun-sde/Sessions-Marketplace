from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from rest_framework import status


class ConflictException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Conflict with the current state of the resource.'
    default_code = 'conflict'

    def __init__(self, detail=None, code=None, message=None):
        actual_detail = message if message is not None else detail
        if actual_detail is None:
            actual_detail = self.default_detail
        if code is not None:
            self.default_code = code
        super().__init__(detail=actual_detail, code=code or self.default_code)


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler providing consistent error shape:
    {
        "error": {
            "code": "error_code",
            "message": "Human readable message",
            "details": {...} (optional)
        }
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_code = getattr(exc, 'default_code', 'error')
        if hasattr(exc, 'get_codes'):
            codes = exc.get_codes()
            if isinstance(codes, str):
                error_code = codes
            elif isinstance(codes, list) and codes:
                error_code = str(codes[0])
            elif isinstance(codes, dict) and codes:
                first_key = next(iter(codes))
                val = codes[first_key]
                error_code = str(val[0]) if isinstance(val, list) and val else str(val)

        message = str(exc.detail) if hasattr(exc, 'detail') else str(exc)
        if isinstance(getattr(exc, 'detail', None), dict):
            # Extract first readable message from detail dict
            first_key = next(iter(exc.detail))
            first_val = exc.detail[first_key]
            if isinstance(first_val, list) and first_val:
                message = f"{first_key}: {first_val[0]}"
            else:
                message = f"{first_key}: {first_val}"
        elif isinstance(getattr(exc, 'detail', None), list) and exc.detail:
            message = str(exc.detail[0])

        error_payload = {
            "code": error_code,
            "message": message,
        }

        if isinstance(getattr(exc, 'detail', None), (dict, list)):
            error_payload["details"] = response.data

        response.data = {"error": error_payload}

    return response
