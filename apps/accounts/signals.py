from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from datetime import datetime
from .models import User, StaffProfile
from apps.students.models import Student
from apps.faculty.models import FacultyProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        role = str(instance.role).upper()
        
        # Wrapping creation in a transaction to ensure atomicity
        with transaction.atomic():
            # --- RBAC Role Synchronization ---
            from .models import Role
            role_obj, _ = Role.objects.get_or_create(role_name=role)
            instance.roles.add(role_obj)

            if role == 'STUDENT':
                # Get academic branch from context if provided by view/form
                branch = getattr(instance, '_academic_branch_context', None)
                Student.objects.get_or_create(
                    user=instance,
                    defaults={
                        'roll_number': instance.login_id,
                        'enrollment_number': instance.enrollment_id or instance.login_id,
                        'branch': branch,
                        'department': branch.program.dept if (branch and branch.program) else None,
                        'program': branch.program if branch else None,
                        'batch_year': datetime.now().year,
                        'admission_date': datetime.now().date(),
                        'status': 'active'
                    }
                )
            elif role in ['FACULTY', 'TEACHER', 'HOD']:
                # Get department from context if provided
                dept = getattr(instance, '_academic_dept_context', None)
                FacultyProfile.objects.get_or_create(
                    user=instance,
                    defaults={
                        'employee_id': instance.login_id,
                        'department': dept
                    }
                )
            elif role != 'ADMIN':
                # All other staff roles
                StaffProfile.objects.get_or_create(
                    user=instance,
                    defaults={'employee_id': instance.login_id}
                )

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Ensure profiles are saved whenever the user is saved."""
    try:
        if hasattr(instance, 'student_profile') and instance.student_profile:
            instance.student_profile.save()
        if hasattr(instance, 'faculty_profile') and instance.faculty_profile:
            instance.faculty_profile.save()
        if hasattr(instance, 'staff_profile') and instance.staff_profile:
            instance.staff_profile.save()
    except Exception:
        # Avoid recursive or failed saves during complex updates
        pass


from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from .models import SecurityLog
from .utils import get_client_ip
import logging

logger = logging.getLogger('security')

@receiver(user_logged_in)
def log_user_logged_in(sender, request, user, **kwargs):
    ip_address = get_client_ip(request) if request else 'Unknown'
    user_agent = request.META.get('HTTP_USER_AGENT', '') if request else 'Unknown'
    
    SecurityLog.objects.create(
        event_type='LOGIN_SUCCESS',
        login_id=user.login_id,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        path=request.path if request else '',
        details="User logged in successfully."
    )
    logger.info(f"LOGIN_SUCCESS - User: {user.login_id} - IP: {ip_address}")


@receiver(user_logged_out)
def log_user_logged_out(sender, request, user, **kwargs):
    if user:
        ip_address = get_client_ip(request) if request else 'Unknown'
        user_agent = request.META.get('HTTP_USER_AGENT', '') if request else 'Unknown'
        
        SecurityLog.objects.create(
            event_type='LOGOUT',
            login_id=user.login_id,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            path=request.path if request else '',
            details="User logged out successfully."
        )
        logger.info(f"LOGOUT - User: {user.login_id} - IP: {ip_address}")


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request=None, **kwargs):
    ip_address = get_client_ip(request) if request else 'Unknown'
    user_agent = request.META.get('HTTP_USER_AGENT', '') if request else 'Unknown'
    login_id = credentials.get('username') or credentials.get('login_id') or 'Unknown'
    
    SecurityLog.objects.create(
        event_type='LOGIN_FAILED',
        login_id=login_id,
        ip_address=ip_address,
        user_agent=user_agent,
        path=request.path if request else '',
        details=f"Failed login attempt with username/login_id: {login_id}"
    )
    logger.warning(f"LOGIN_FAILED - Attempted User: {login_id} - IP: {ip_address}")

