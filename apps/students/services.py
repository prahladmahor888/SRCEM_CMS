from apps.core import excel_utils as pd
from django.db import transaction, models
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from apps.accounts.models import User
from apps.students.models import Student
from apps.core.models import College, Department, Program, Branch
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

class BulkAdmissionService:
    @staticmethod
    def validate_excel_structure(sheets_dict):
        """Validates that required sheets and columns are present."""
        required_sheets = ['users', 'students']
        for sheet in required_sheets:
            if sheet not in sheets_dict:
                raise ValidationError(f"Missing required sheet: '{sheet}'")

        # Column validation
        user_cols = ['login_id', 'role', 'college_id', 'first_name'] # Minimum required
        student_cols = ['user_id', 'roll_number', 'department_id', 'program_id', 'branch_id']
        
        for col in user_cols:
            if col not in sheets_dict['users'].columns:
                raise ValidationError(f"Sheet 'users' missing required column: '{col}'")
        
        for col in student_cols:
            if col not in sheets_dict['students'].columns:
                raise ValidationError(f"Sheet 'students' missing required column: '{col}'")

    @classmethod
    def execute_import(cls, sheets_dict, dry_run=False, update_existing=False):
        """
        Executes the bulk import process.
        sheets_dict: dict of DataFrames {sheet_name: df}
        """
        users_df = sheets_dict['users'].fillna('')
        students_df = sheets_dict['students'].fillna('')
        
        results = {
            'status': 'success',
            'inserted': 0,
            'updated': 0,
            'errors': []
        }

        try:
            with transaction.atomic():
                # 1. Relational Validation (Cache lookups for performance)
                colleges = {c.id: c for c in College.objects.all()}
                departments = {d.id: d for d in Department.objects.all()}
                programs = {p.id: p for p in Program.objects.all()}
                branches = {b.id: b for b in Branch.objects.all()}

                # 2. Process Users
                user_map = {} # Excel ID -> User Object
                users_to_create = []
                
                for index, row in users_df.iterrows():
                    excel_id = row.get('id')
                    login_id = str(row.get('login_id')).strip()
                    email = str(row.get('email', '')).strip() or None
                    college_id = row.get('college_id')

                    # Validation
                    if not login_id:
                        results['errors'].append({'sheet': 'users', 'row': index + 2, 'message': "login_id is required"})
                        continue
                    
                    if college_id not in colleges:
                        results['errors'].append({'sheet': 'users', 'row': index + 2, 'message': f"Invalid college_id: {college_id}"})
                        continue

                    # Check for existing user
                    existing_user = User.objects.filter(login_id=login_id).first()
                    if existing_user:
                        if not update_existing:
                            results['errors'].append({'sheet': 'users', 'row': index + 2, 'message': f"User with login_id {login_id} already exists"})
                            continue
                        else:
                            # Update existing (simplified for bulk)
                            existing_user.first_name = row.get('first_name')
                            existing_user.last_name = row.get('last_name', '')
                            existing_user.email = email
                            existing_user.college = colleges[college_id]
                            if not dry_run: existing_user.save()
                            user_map[excel_id] = existing_user
                            results['updated'] += 1
                            continue

                    user = User(
                        login_id=login_id,
                        enrollment_id=row.get('enrollment_id'),
                        role=row.get('role', 'STUDENT'),
                        college=colleges[college_id],
                        first_name=row.get('first_name'),
                        last_name=row.get('last_name', ''),
                        email=email,
                        phone=row.get('phone', ''),
                        is_active=row.get('is_active', True),
                        is_staff=row.get('is_staff', False),
                        is_superuser=row.get('is_superuser', False),
                        two_step_enabled=row.get('two_step_enabled', False),
                        password=make_password('Welcome@123') # Default password
                    )
                    users_to_create.append((excel_id, user))

                if results['errors']:
                    results['status'] = 'failed'
                    raise ValidationError("Data validation failed")

                # Bulk Create Users
                if not dry_run:
                    # Note: bulk_create doesn't return IDs reliably in all DBs. 
                    # We create them one by one if we need to map IDs for related objects, 
                    # OR we use a unique field (login_id) to map them.
                    # For MySQL/Postgres, we can use bulk_create and then re-fetch.
                    created_users = User.objects.bulk_create([u[1] for u in users_to_create], batch_size=200)
                    # Refresh user_map with created objects
                    for excel_id, u_obj in users_to_create:
                        # Fetch from DB to get the ID
                        user_map[excel_id] = User.objects.get(login_id=u_obj.login_id)
                else:
                    for excel_id, u_obj in users_to_create:
                        user_map[excel_id] = u_obj # Mock object for dry run

                # 3. Process Students
                students_to_create = []
                for index, row in students_df.iterrows():
                    excel_user_id = row.get('user_id')
                    roll_number = str(row.get('roll_number')).strip()
                    dept_id = row.get('department_id')
                    prog_id = row.get('program_id')
                    branch_id = row.get('branch_id')

                    if excel_user_id not in user_map:
                        results['errors'].append({'sheet': 'students', 'row': index + 2, 'message': f"user_id {excel_user_id} not found in users sheet"})
                        continue

                    if dept_id not in departments:
                        results['errors'].append({'sheet': 'students', 'row': index + 2, 'message': f"Invalid department_id: {dept_id}"})
                        continue

                    student = Student(
                        user=user_map[excel_user_id],
                        roll_number=roll_number,
                        enrollment_number=row.get('enrollment_number'),
                        department=departments.get(dept_id),
                        program=programs.get(prog_id),
                        branch=branches.get(branch_id),
                        semester=row.get('semester', 1),
                        section=row.get('section', 'A'),
                        admission_date=row.get('admission_date') or timezone.now().date(),
                        batch_year=row.get('batch_year'),
                        status=row.get('status', 'active'),
                        date_of_birth=row.get('date_of_birth'),
                        gender=row.get('gender', 'male'),
                        blood_group=row.get('blood_group'),
                        phone_alt=row.get('phone_alt'),
                        address=row.get('address'),
                        nationality=row.get('nationality', 'Indian'),
                        category=row.get('category', 'General')
                    )
                    students_to_create.append(student)

                if results['errors']:
                    results['status'] = 'failed'
                    raise ValidationError("Data validation failed")

                if not dry_run:
                    Student.objects.bulk_create(students_to_create, batch_size=200)
                
                results['inserted'] = len(users_to_create) + len(students_to_create)

                if dry_run:
                    transaction.set_rollback(True)
                    results['message'] = "Dry run successful. No data committed."

        except ValidationError as e:
            results['status'] = 'failed'
            if not results['errors']:
                results['errors'].append({'sheet': 'system', 'row': 0, 'message': str(e)})
        except Exception as e:
            results['status'] = 'failed'
            results['errors'].append({'sheet': 'system', 'row': 0, 'message': f"Unexpected error: {str(e)}"})
            logger.exception("Bulk admission failed")

        return results
