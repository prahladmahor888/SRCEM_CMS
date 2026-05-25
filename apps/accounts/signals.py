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
