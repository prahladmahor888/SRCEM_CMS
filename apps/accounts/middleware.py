import logging
import traceback
from django.utils.deprecation import MiddlewareMixin
from .utils import get_client_ip
from .models import SecurityLog

logger = logging.getLogger('security')

class SecurityMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware to monitor and log security-related issues,
    such as unhandled exceptions (500s) and unauthorized access attempts (403s/404s).
    """
    def process_exception(self, request, exception):
        """
        Log unhandled exceptions (HTTP 500 equivalent) as system errors.
        """
        ip_address = get_client_ip(request)
        user = request.user if request.user.is_authenticated else None
        login_id = user.login_id if user else None
        
        tb = traceback.format_exc()
        details = f"Exception: {str(exception)}\n\nTraceback:\n{tb}"
        
        # Log to Database safely
        try:
            SecurityLog.objects.create(
                event_type='ERROR',
                login_id=login_id,
                user=user,
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                path=request.path,
                details=details
            )
        except Exception as log_err:
            logger.warning(f"Failed to record SecurityLog: {log_err}")
        
        # Log to security log file
        logger.error(
            f"ERROR - IP: {ip_address} - User: {login_id or 'Anonymous'} - Path: {request.path} - {str(exception)}"
        )
        return None

    def process_response(self, request, response):
        """
        Log client errors such as 400 Bad Request, 403 Forbidden (Unauthorized),
        and suspicious 404s.
        """
        if response.status_code in [400, 403, 404]:
            # Prevent excessive logging for typical 404 assets by ignoring common static/media files
            if response.status_code == 404 and (
                request.path.startswith('/static/') or 
                request.path.startswith('/media/') or 
                'favicon.ico' in request.path
            ):
                return response

            user = request.user if request.user.is_authenticated else None
            login_id = user.login_id if user else None
            ip_address = get_client_ip(request)
            
            event_type = 'UNAUTHORIZED_ACCESS' if response.status_code == 403 else 'SUSPICIOUS'
            details = f"HTTP {response.status_code} returned for path {request.path}."
            
            # Log to Database
            SecurityLog.objects.create(
                event_type=event_type,
                login_id=login_id,
                user=user,
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                path=request.path,
                details=details
            )
            
            # Log to security log file
            logger.warning(
                f"{event_type} - IP: {ip_address} - User: {login_id or 'Anonymous'} - Path: {request.path} - Status: {response.status_code}"
            )
            
        return response


import time

traffic_logger = logging.getLogger('traffic')

class TrafficMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware to capture and log general HTTP request/response traffic details
    to the traffic log file.
    """
    def process_request(self, request):
        request._start_time = time.time()

    def process_response(self, request, response):
        # Prevent logging static and media assets to keep log size clean
        if request.path.startswith('/static/') or request.path.startswith('/media/') or 'favicon.ico' in request.path:
            return response

        duration = 0
        if hasattr(request, '_start_time'):
            duration = int((time.time() - request._start_time) * 1000)
            
        ip_address = get_client_ip(request)
        user = request.user if request.user.is_authenticated else None
        login_id = user.login_id if user else 'Anonymous'
        method = request.method
        path = request.path
        status_code = response.status_code
        content_length = len(response.content) if hasattr(response, 'content') else 0
        
        # Log traffic details
        log_msg = f"TRAFFIC - IP: {ip_address} - User: {login_id} - Method: {method} - Path: {path} - Status: {status_code} - Size: {content_length}B - Time: {duration}ms"
        traffic_logger.info(log_msg)
        
        return response


from django.core.cache import cache
from django.http import JsonResponse, HttpResponse

class RateLimitMiddleware(MiddlewareMixin):
    """
    Middleware to prevent brute-force attacks on AJAX and authentication views
    using Django's cache framework.
    """
    def process_request(self, request):
        path = request.path
        ip_address = get_client_ip(request)
        
        # Determine if it's an AJAX/API request or a login request
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or ('application/json' in request.content_type if request.content_type else False)
        is_login = 'login' in path.lower()
        
        # Rate limit POST/PUT/DELETE requests for API/AJAX and POST for logins
        if not (is_login or (is_ajax and request.method in ['POST', 'PUT', 'DELETE'])):
            return None

        # Define limits (number of requests, period in seconds)
        if is_login:
            limit = 5      # Max 5 attempts
            period = 60    # per 60 seconds (1 minute)
            cache_key = f"rl_login_{ip_address}"
            msg = "Too many login attempts. Please try again in a minute."
        else:
            limit = 30     # Max 30 requests
            period = 60    # per 60 seconds
            cache_key = f"rl_ajax_{ip_address}_{path}"
            msg = "Rate limit exceeded. Too many requests."

        # Check request count in cache
        request_count = cache.get(cache_key, 0)
        
        if request_count >= limit:
            # Log suspicious activity/bruteforce block
            user = request.user if request.user.is_authenticated else None
            login_id = user.login_id if user else request.POST.get('username') or request.POST.get('login_id') or 'Unknown'
            
            SecurityLog.objects.create(
                event_type='SUSPICIOUS',
                login_id=login_id,
                user=user,
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                path=path,
                details=f"Brute-force / Rate limit blocked. Key: {cache_key}. Count: {request_count} (Limit: {limit})."
            )
            
            logger.warning(f"RATE_LIMIT_BLOCKED - IP: {ip_address} - Path: {path} - Attempts: {request_count}")
            
            if is_ajax or 'application/json' in request.headers.get('Accept', ''):
                return JsonResponse({'status': 'error', 'message': msg}, status=429)
            else:
                return HttpResponse(f"<h1>429 Too Many Requests</h1><p>{msg}</p>", status=429)

        # Increment count
        if request_count == 0:
            cache.set(cache_key, 1, period)
        else:
            cache.incr(cache_key)

        return None


