from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from apps.accounts.models import User
from apps.faculty.models import FacultyProfile
from apps.core.models import College, Department, Program, Branch, Subject, StudyMaterial
from django.core.exceptions import ValidationError
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class BulkFacultyService:
    @classmethod
    def execute_import(cls, sheets_dict, dry_run=False, update_existing=False):
        users_df = sheets_dict.get('users', pd.DataFrame()).fillna('')
        faculty_df = sheets_dict.get('faculty', pd.DataFrame()).fillna('')
        
        results = {'status': 'success', 'inserted': 0, 'updated': 0, 'errors': []}

        try:
            with transaction.atomic():
                colleges = {c.id: c for c in College.objects.all()}
                departments = {d.id: d for d in Department.objects.all()}
                
                user_map = {}
                users_to_create = []

                # 1. Process Users
                for index, row in users_df.iterrows():
                    login_id = str(row.get('login_id')).strip()
                    college_id = row.get('college_id')
                    if not login_id or college_id not in colleges:
                        results['errors'].append({'sheet': 'users', 'row': index + 2, 'message': "Invalid login_id or college_id"})
                        continue

                    existing_user = User.objects.filter(login_id=login_id).first()
                    if existing_user:
                        if update_existing:
                            existing_user.first_name = row.get('first_name')
                            if not dry_run: existing_user.save()
                            user_map[row.get('id')] = existing_user
                            results['updated'] += 1
                        continue

                    user = User(
                        login_id=login_id,
                        role='TEACHER',
                        college=colleges[college_id],
                        first_name=row.get('first_name'),
                        last_name=row.get('last_name', ''),
                        email=row.get('email', ''),
                        password=make_password('Welcome@123')
                    )
                    users_to_create.append((row.get('id'), user))

                if not dry_run:
                    for eid, uobj in users_to_create:
                        uobj.save()
                        user_map[eid] = uobj
                else:
                    for eid, uobj in users_to_create: user_map[eid] = uobj

                # 2. Process Faculty
                faculty_to_create = []
                for index, row in faculty_df.iterrows():
                    excel_user_id = row.get('user_id')
                    dept_id = row.get('department_id')
                    emp_id = str(row.get('employee_id')).strip()

                    if excel_user_id not in user_map or not emp_id:
                        results['errors'].append({'sheet': 'faculty', 'row': index + 2, 'message': f"Invalid user_id or employee_id"})
                        continue

                    f_profile = FacultyProfile(
                        user=user_map[excel_user_id],
                        department=departments.get(dept_id),
                        employee_id=emp_id,
                        designation=row.get('designation'),
                        qualification=row.get('qualification'),
                        joining_date=row.get('joining_date') or timezone.now().date()
                    )
                    faculty_to_create.append(f_profile)

                if not dry_run:
                    FacultyProfile.objects.bulk_create(faculty_to_create)
                
                results['inserted'] = len(users_to_create) + len(faculty_to_create)
                if dry_run: transaction.set_rollback(True)

        except Exception as e:
            results['status'] = 'failed'
            results['errors'].append({'sheet': 'system', 'row': 0, 'message': str(e)})
        
        return results

class BulkCoreService:
    """Generic high-performance service for core models like Branch and StudyMaterial."""
    
    @classmethod
    def import_branches(cls, df, dry_run=False):
        results = {'status': 'success', 'inserted': 0, 'updated': 0, 'errors': []}
        try:
            with transaction.atomic():
                programs = {p.id: p for p in Program.objects.all()}
                to_create = []
                for index, row in df.iterrows():
                    prog_id = row.get('program_id')
                    code = str(row.get('branch_code')).strip()
                    if prog_id not in programs or not code:
                        results['errors'].append({'sheet': 'branches', 'row': index + 2, 'message': "Invalid program_id or code"})
                        continue
                    
                    branch = Branch(
                        program=programs[prog_id],
                        branch_name=row.get('branch_name'),
                        branch_code=code,
                        duration_years=row.get('duration_years', 4)
                    )
                    to_create.append(branch)
                
                if not dry_run: Branch.objects.bulk_create(to_create)
                results['inserted'] = len(to_create)
                if dry_run: transaction.set_rollback(True)
        except Exception as e:
            results['status'] = 'failed'
            results['errors'].append({'sheet': 'system', 'row': 0, 'message': str(e)})
        return results

    @classmethod
    def import_study_material(cls, df, dry_run=False):
        results = {'status': 'success', 'inserted': 0, 'updated': 0, 'errors': []}
        try:
            with transaction.atomic():
                subjects = {s.id: s for s in Subject.objects.all()}
                faculty = {f.id: f for f in FacultyProfile.objects.all()}
                to_create = []
                for index, row in df.iterrows():
                    subj_id = row.get('subject_id')
                    fac_id = row.get('faculty_id')
                    if subj_id not in subjects:
                        results['errors'].append({'sheet': 'materials', 'row': index + 2, 'message': "Invalid subject_id"})
                        continue
                    
                    mat = StudyMaterial(
                        subject=subjects[subj_id],
                        faculty=faculty.get(fac_id),
                        title=row.get('title'),
                        material_type=row.get('material_type', 'notes'),
                        video_url=row.get('video_url'),
                        description=row.get('description')
                    )
                    to_create.append(mat)
                
                if not dry_run: StudyMaterial.objects.bulk_create(to_create)
                results['inserted'] = len(to_create)
                if dry_run: transaction.set_rollback(True)
        except Exception as e:
            results['status'] = 'failed'
            results['errors'].append({'sheet': 'system', 'row': 0, 'message': str(e)})
        return results
