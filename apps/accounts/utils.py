def get_client_ip(request):
    """
    Get the client IP address from request META.
    Takes into account reverse proxies like Nginx/Cloudflare using HTTP_X_FORWARDED_FOR.
    """
    if not request:
        return 'Unknown'
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
