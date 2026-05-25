"""
URL configuration for SRCEM_CMS project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import os
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

from django.views.generic import TemplateView

from apps.core.views import PublicHomeView, AboutUsView, PlacementsView, PlacementListView

urlpatterns = [
    path('', PublicHomeView.as_view(), name='home'),
    path('about-us/', AboutUsView.as_view(), name='about_us'),
    path('student-erp/', TemplateView.as_view(template_name='student_erp.html'), name='student_erp'),
    path('digital-library/', TemplateView.as_view(template_name='digital_library.html'), name='digital_library'),
    path('placements/', PlacementsView.as_view(), name='placements'),
    path('placements/all/', PlacementListView.as_view(), name='placements_list'),
    path('transport/', TemplateView.as_view(template_name='transport.html'), name='transport'),
    path('admin/', admin.site.urls),
    path('', include('apps.accounts.urls')),
    path('', include('apps.dashboard.urls')),
    path('', include('apps.faculty.urls')),
    path('', include('apps.fees.urls')),
    path('', include('apps.students.urls')),
    
    # Error pages preview
    path('400/', TemplateView.as_view(template_name='errors/400/400.html'), name='error_400'),
    path('403/', TemplateView.as_view(template_name='errors/403/403.html'), name='error_403'),
    path('404/', TemplateView.as_view(template_name='errors/404/404.html'), name='error_404'),
    path('500/', TemplateView.as_view(template_name='errors/500/500.html'), name='error_500'),
]

# Custom error handlers for production
handler400 = 'SRCEM_CMS.views.error_400'
handler403 = 'SRCEM_CMS.views.error_403'
handler404 = 'SRCEM_CMS.views.error_404'
handler500 = 'SRCEM_CMS.views.error_500'


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve, {'document_root': os.path.join(settings.BASE_DIR, 'static')}),
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
