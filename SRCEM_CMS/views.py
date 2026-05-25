from django.shortcuts import render

def error_404(request, exception=None):
    return render(request, 'errors/404/404.html', status=404)

def error_500(request):
    return render(request, 'errors/500/500.html', status=500)

def error_403(request, exception=None):
    return render(request, 'errors/403/403.html', status=403)

def error_400(request, exception=None):
    return render(request, 'errors/400/400.html', status=400)
