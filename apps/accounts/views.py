from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.urls import reverse_lazy
from django.db import transaction
from django.views import View
from django.contrib.auth.models import Group

from apps.core.views import ERPListView, ERPCreateView, ERPUpdateView, ERPDetailView, RolePermissionMixin
from apps.accounts.models import User, StaffProfile, IDCounter, Role, Permission, SecurityLog
from apps.accounts.forms import UserCreationForm
from apps.accounts.utils import get_client_ip
from apps.students.models import Student
from apps.faculty.models import FacultyProfile

# --- USER MODULE ---
class UserListView(RolePermissionMixin, ERPListView):
    model = User
    module_name = "User"
    list_fields = ['login_id', 'role', 'first_name', 'last_name', 'email', 'phone', 'is_active', 'date_joined']
    paginate_by = 10
    required_permission = 'can_view_users'

class UserCreateView(RolePermissionMixin, ERPCreateView):
    model = User
    module_name = "User"
    form_class = UserCreationForm
    success_url = reverse_lazy('user_list')
    required_permission = 'can_manage_users'

    def form_valid(self, form):
        role = form.cleaned_data.get('role')
        if role:
            role = str(role).upper()
            
        academic_code = None
        if role == 'STUDENT':
            branch = form.cleaned_data.get('academic_branch')
            if branch:
                academic_code = branch.branch_code
                form.instance._academic_branch_context = branch
        elif role in ['FACULTY', 'HOD', 'TEACHER']:
            dept = form.cleaned_data.get('academic_department')
            if dept:
                academic_code = dept.dept_code
                form.instance._academic_dept_context = dept
            form.instance._qualification_context = form.cleaned_data.get('qualification')
            form.instance._designation_context = form.cleaned_data.get('designation')
            form.instance._joining_date_context = form.cleaned_data.get('joining_date')
        elif role in ['ADMIN', 'SUB_ADMIN', 'ACCOUNTANT', 'ADMISSION']:
            form.instance._joining_date_context = form.cleaned_data.get('joining_date')
        
        form.instance._academic_code_context = academic_code
        
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                user = self.object
                
                if role == 'STUDENT':
                    profile = user.student_profile
                    if form.cleaned_data.get('roll_number'): profile.roll_number = form.cleaned_data.get('roll_number')
                    if form.cleaned_data.get('semester'): profile.semester = form.cleaned_data.get('semester')
                    if form.cleaned_data.get('admission_date'): profile.admission_date = form.cleaned_data.get('admission_date')
                    if form.cleaned_data.get('batch_year'): profile.batch_year = form.cleaned_data.get('batch_year')
                    profile.save()
                elif role in ['FACULTY', 'HOD', 'TEACHER']:
                    profile = user.faculty_profile
                    if form.cleaned_data.get('designation'): profile.designation = form.cleaned_data.get('designation')
                    if form.cleaned_data.get('qualification'): profile.qualification = form.cleaned_data.get('qualification')
                    if form.cleaned_data.get('joining_date'): profile.joining_date = form.cleaned_data.get('joining_date')
                    profile.save()
                
                return response
        except Exception as e:
            form.add_error(None, f"Error saving profile data: {str(e)}")
            return self.form_invalid(form)

class UserUpdateView(RolePermissionMixin, ERPUpdateView):
    model = User
    module_name = "User"
    fields = [
        'login_id', 'role', 'college', 
        'first_name', 'last_name', 'email', 'phone', 
        'is_active', 'is_staff', 'profile_image'
    ]
    success_url = reverse_lazy('user_list')
    required_permission = 'can_manage_users'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if 'login_id' in form.fields:
            form.fields['login_id'].disabled = True
        return form

class UserDetailView(RolePermissionMixin, ERPDetailView):
    model = User
    module_name = "User"
    detail_fields = ['role', 'login_id', 'first_name', 'last_name', 'email', 'phone', 'is_active', 'date_joined']
    required_permission = 'can_view_users'


# --- SECURITY & RBAC MODULES ---

class RoleListView(RolePermissionMixin, ERPListView):
    model = Role
    module_name = "User Role"
    list_fields = ['role_name']
    required_permission = 'can_manage_users'

class RoleDetailView(RolePermissionMixin, ERPDetailView):
    model = Role
    module_name = "User Role"
    required_permission = 'can_manage_users'

class RoleCreateView(ERPCreateView):
    model = Role
    module_name = "User Role"
    fields = ['role_name', 'permissions']
    success_url = reverse_lazy('role_list')

class RoleUpdateView(ERPUpdateView):
    model = Role
    module_name = "User Role"
    fields = ['role_name', 'permissions']
    success_url = reverse_lazy('role_list')

class PermissionListView(RolePermissionMixin, ERPListView):
    model = Permission
    module_name = "System Permission"
    list_fields = ['permission_name']
    required_permission = 'can_manage_users'

class PermissionDetailView(RolePermissionMixin, ERPDetailView):
    model = Permission
    module_name = "System Permission"
    required_permission = 'can_manage_users'

class PermissionCreateView(ERPCreateView):
    model = Permission
    module_name = "System Permission"
    fields = ['permission_name']
    success_url = reverse_lazy('permission_list')

class PermissionUpdateView(ERPUpdateView):
    model = Permission
    module_name = "System Permission"
    fields = ['permission_name']
    success_url = reverse_lazy('permission_list')

class GroupListView(RolePermissionMixin, ERPListView):
    model = Group
    module_name = "User Group"
    list_fields = ['name']
    required_permission = 'can_manage_users'

class GroupDetailView(RolePermissionMixin, ERPDetailView):
    model = Group
    module_name = "User Group"
    required_permission = 'can_manage_users'

class GroupCreateView(ERPCreateView):
    model = Group
    module_name = "User Group"
    fields = ['name', 'permissions']
    success_url = reverse_lazy('group_list')

class GroupUpdateView(ERPUpdateView):
    model = Group
    module_name = "User Group"
    fields = ['name', 'permissions']
    success_url = reverse_lazy('group_list')

@login_required
def profile_view(request):
    """Premium profile view handling self-service updates and dynamic person-based data."""
    user = request.user
    role = str(user.role).upper()
    
    profile = None
    if role == 'STUDENT':
        profile = getattr(user, 'student_profile', None)
    elif role in ['FACULTY', 'HOD']:
        profile = getattr(user, 'faculty_profile', None)
    else:
        profile = getattr(user, 'staff_profile', None)

    if request.method == 'POST':
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        
        if phone: user.phone = phone
        if email: user.email = email
            
        if 'profile_image' in request.FILES:
            if user.role == 'ADMIN':
                user.profile_image = request.FILES['profile_image']
            else:
                messages.error(request, "Only Administrators can change profile images.")
            
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        if new_password:
            if new_password == confirm_password:
                user.set_password(new_password)
                update_session_auth_hash(request, user)
                messages.success(request, "Password updated successfully!")
                
                # Log password change security event
                SecurityLog.objects.create(
                    event_type='PASSWORD_CHANGE',
                    login_id=user.login_id,
                    user=user,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    path=request.path,
                    details="User changed password from their profile page."
                )
            else:
                messages.error(request, "Passwords do not match.")

        two_step = request.POST.get('two_step_enabled') == 'on'
        user.two_step_enabled = two_step

        user.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('profile')

    # Load dynamic activity logs for this user from SecurityLog
    recent_security_logs = SecurityLog.objects.filter(user=user)[:15]
    recent_logs = []
    for log in recent_security_logs:
        icon = 'fa-circle-info'
        color = 'blue'
        if log.event_type == 'LOGIN_SUCCESS':
            icon = 'fa-right-to-bracket'
            color = 'blue'
        elif log.event_type == 'LOGIN_FAILED':
            icon = 'fa-triangle-exclamation'
            color = 'red'
        elif log.event_type == 'LOGOUT':
            icon = 'fa-right-from-bracket'
            color = 'orange'
        elif log.event_type == 'PASSWORD_CHANGE':
            icon = 'fa-key'
            color = 'purple'
        elif log.event_type == 'UNAUTHORIZED_ACCESS':
            icon = 'fa-shield-halved'
            color = 'red'
        elif log.event_type == 'ERROR':
            icon = 'fa-bug'
            color = 'red'
            
        recent_logs.append({
            'action': log.get_event_type_display(),
            'time': log.timestamp.strftime('%d %b %Y, %H:%M') if log.timestamp else 'Just now',
            'icon': icon,
            'color': color,
            'ip': log.ip_address
        })
        
    if not recent_logs:
        recent_logs = [
            {'action': 'Profile Created', 'time': user.date_joined.strftime('%d %b %Y, %H:%M') if user.date_joined else 'Today', 'icon': 'fa-user-plus', 'color': 'blue', 'ip': 'System'},
        ]

    context = {
        'user': user,
        'profile': profile,
        'role_display': user.get_role_display(),
        'recent_logs': recent_logs
    }
    return render(request, 'dashboard/profile.html', context)

# --- STAFF REGISTRY MODULE ---
class StaffRegistryListView(RolePermissionMixin, ERPListView):
    model = User
    module_name = "Staff Registry"
    list_fields = ['login_id', 'role', 'first_name', 'last_name', 'email', 'is_active']
    required_permission = 'can_manage_users'
    create_url = 'staff-registry/add/'

    def get_queryset(self):
        # Only show staff roles (non-student, non-teacher/faculty)
        staff_roles = ['ACCOUNTANT', 'ADMISSION', 'LAB', 'PLACEMENT', 'STAFF', 'LIBRARIAN']
        return User.objects.filter(role__in=staff_roles).order_by('-date_joined')

class StaffRegistryCreateView(RolePermissionMixin, ERPCreateView):
    model = User
    module_name = "Staff Member"
    form_class = UserCreationForm
    success_url = reverse_lazy('staff_list')
    required_permission = 'can_manage_users'

    def form_valid(self, form):
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                user = self.object
                
                # Create/Update Staff Profile
                profile = user.staff_profile
                if form.cleaned_data.get('employee_id'): 
                    profile.employee_id = form.cleaned_data.get('employee_id')
                if form.cleaned_data.get('staff_department'):
                    profile.department = form.cleaned_data.get('staff_department')
                profile.save()
                
                return response
        except Exception as e:
            form.add_error(None, f"Error creating staff profile: {str(e)}")
            return self.form_invalid(form)

class StaffRegistryUpdateView(RolePermissionMixin, ERPUpdateView):
    model = User
    module_name = "Staff Member"
    fields = ['role', 'first_name', 'last_name', 'email', 'phone', 'is_active']
    success_url = reverse_lazy('staff_list')
    required_permission = 'can_manage_users'


class SecurityLogListView(RolePermissionMixin, ERPListView):
    model = SecurityLog
    module_name = "Security Log"
    list_fields = ['event_type', 'login_id', 'ip_address', 'path', 'timestamp']
    paginate_by = 25
    required_permission = 'can_manage_users'

    def get_queryset(self):
        return SecurityLog.objects.all().order_by('-timestamp')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_add'] = False
        context['can_edit'] = False
        # Prevent bulk operations for security log safety
        context['can_delete'] = False
        return context


class SecurityLogDetailView(RolePermissionMixin, ERPDetailView):
    model = SecurityLog
    module_name = "Security Log"
    detail_fields = ['event_type', 'login_id', 'ip_address', 'path', 'user_agent', 'details', 'timestamp']
    required_permission = 'can_manage_users'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_add'] = False
        context['can_edit'] = False
        return context

