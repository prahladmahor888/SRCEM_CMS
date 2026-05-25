from django.core.management.base import BaseCommand
from apps.accounts.models import Role, Permission
from django.db import transaction

class Command(BaseCommand):
    help = 'Assigns registry and departmental permissions to the HOD role.'

    def handle(self, *args, **options):
        permissions_to_assign = [
            'can_view_academic_registry',
            'can_manage_students',
            'can_manage_faculty',
            'can_view_dept_data',
            'can_view_subjects',
            'can_manage_subjects',
            'can_manage_academic',
        ]

        try:
            with transaction.atomic():
                # 1. Ensure HOD role exists
                hod_role, _ = Role.objects.get_or_create(role_name='HOD')

                # 2. Assign permissions
                for perm_name in permissions_to_assign:
                    perm_obj, _ = Permission.objects.get_or_create(permission_name=perm_name)
                    hod_role.permissions.add(perm_obj)
                
                hod_role.save()

                # 3. Link existing HOD users to the Role object
                from apps.accounts.models import User
                hod_users = User.objects.filter(role='HOD')
                count = 0
                for user in hod_users:
                    if not user.roles.filter(id=hod_role.id).exists():
                        user.roles.add(hod_role)
                        count += 1

            self.stdout.write(self.style.SUCCESS(f'Successfully assigned HOD permissions and linked {count} existing HOD users.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error assigning permissions: {e}'))
