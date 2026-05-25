from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, StaffProfile, IDCounter, Role, Permission
from apps.students.models import Student
from apps.faculty.models import FacultyProfile

class StudentInline(admin.StackedInline):
    model = Student
    can_delete = False
    verbose_name_plural = 'Student Profile'
    fk_name = 'user'

class FacultyProfileInline(admin.StackedInline):
    model = FacultyProfile
    can_delete = False
    verbose_name_plural = 'Faculty Profile'
    fk_name = 'user'

class StaffProfileInline(admin.StackedInline):
    model = StaffProfile
    can_delete = False
    verbose_name_plural = 'Staff Profile'
    fk_name = 'user'

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('login_id', 'get_full_name', 'email', 'is_staff', 'is_active')
    list_filter = ('roles', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('login_id', 'first_name', 'last_name', 'email')
    ordering = ('login_id',)
    
    fieldsets = (
        ('Authentication', {'fields': ('login_id', 'password')}),
        ('Role & Roles', {'fields': ('role', 'roles', 'college')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone', 'profile_image')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    filter_horizontal = ('roles', 'groups', 'user_permissions')

    def get_inline_instances(self, request, obj=None):
        inlines = []
        if obj:
            # Check for linked profiles
            if hasattr(obj, 'student_profile'):
                inlines.append(StudentInline(self.model, self.admin_site))
            elif hasattr(obj, 'faculty_profile'):
                inlines.append(FacultyProfileInline(self.model, self.admin_site))
            elif hasattr(obj, 'staff_profile'):
                inlines.append(StaffProfileInline(self.model, self.admin_site))
        return inlines

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('role_name',)
    filter_horizontal = ('permissions',)

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('permission_name',)

@admin.register(IDCounter)
class IDCounterAdmin(admin.ModelAdmin):
    list_display = ('prefix', 'last_serial')
    search_fields = ('prefix',)

@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'user', 'department')
    search_fields = ('employee_id', 'user__login_id', 'user__first_name')
