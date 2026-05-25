from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .models import IDCounter

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # Password Reset
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(template_name='accounts/password_reset.html'), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html'), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), 
         name='password_reset_complete'),

    # User Management
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/add/', views.UserCreateView.as_view(), name='user_add'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user_edit'),

    # Staff Registry
    path('staff-registry/', views.StaffRegistryListView.as_view(), name='staff_list'),
    path('staff-registry/add/', views.StaffRegistryCreateView.as_view(), name='staff_add'),
    path('staff-registry/<int:pk>/edit/', views.StaffRegistryUpdateView.as_view(), name='staff_edit'),

    # Role Management
    path('roles/', views.RoleListView.as_view(), name='role_list'),
    path('roles/<int:pk>/', views.RoleDetailView.as_view(), name='role_detail'),
    path('roles/add/', views.RoleCreateView.as_view(), name='role_add'),
    path('roles/<int:pk>/edit/', views.RoleUpdateView.as_view(), name='role_edit'),

    # ID Configuration
    path('id-configs/', views.ERPListView.as_view(model=IDCounter, module_name="ID Configuration", list_fields=['prefix', 'last_serial']), name='id_counter_list'),

    # Profile
    path('profile/', views.profile_view, name='profile'),
]