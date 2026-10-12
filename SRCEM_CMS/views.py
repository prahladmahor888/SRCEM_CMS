import sys
import traceback
from django.shortcuts import render
from django.http import HttpResponse

def error_404(request, exception=None):
    return render(request, 'errors/404.html', status=404)

def error_500(request):
    exc_type, exc_value, tb = sys.exc_info()
    if exc_value:
        error_details = "".join(traceback.format_exception(exc_type, exc_value, tb))
        return HttpResponse(
            f"""<!DOCTYPE html><html><head><title>500 Internal Error</title></head><body style="background:#0f172a;color:#f87171;font-family:monospace;padding:24px;">
            <h2 style="color:#ef4444;border-bottom:1px solid #334155;padding-bottom:10px;">Django 500 Runtime Exception</h2>
            <pre style="background:#1e293b;color:#f1f5f9;padding:16px;border-radius:6px;overflow-x:auto;font-size:13px;border:1px solid #475569;">{error_details}</pre>
            </body></html>""",
            status=500,
            content_type="text/html; charset=utf-8"
        )
    return render(request, 'errors/500.html', status=500)

def error_403(request, exception=None):
    return render(request, 'errors/403.html', status=403)

def error_400(request, exception=None):
    return render(request, 'errors/400.html', status=400)

