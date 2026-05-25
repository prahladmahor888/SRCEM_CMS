from django.core.exceptions import PermissionDenied
from functools import wraps

def role_permission_required(permission_name):
    """
    Decorator for views that checks whether a user has a specific role-based permission.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied
            
            if request.user.has_role_permission(permission_name):
                return view_func(request, *args, **kwargs)
            
            raise PermissionDenied
        return _wrapped_view
    return decorator
