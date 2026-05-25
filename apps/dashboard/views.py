from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from apps.core.views import ERPListView, ERPCreateView, ERPUpdateView, ERPDetailView, RolePermissionMixin
from apps.accounts.models import User, StaffProfile, IDCounter, Role, Permission
from apps.core.models import (
    College, CollegeSettings, Department, Program, Branch, Subject, SubjectTopic, StudyMaterial,
    HeroSlide, PublicNotice, CollegeEvent, HomeProgram, GalleryItem, Recruiter, CollegeStat,
    AboutSectionConfig, PlacementConfig, PlacementAchiever, PlacementTrainingFeature, PlacementProcessStep
)
from apps.core.forms import SubjectForm
from apps.students.models import Student
from apps.faculty.models import FacultyProfile, SubjectAllotment, SubjectSchedule, SyllabusCoverage, ResearchPublication, FacultyDocument
from apps.fees.models import FeeReceipt, FinancialExpense
from .models import HODNotification
from django.db.models import Sum, Avg, Count
from django.contrib.auth.models import Group
from django.db import transaction
from django.views import View
from django.forms import inlineformset_factory
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError
import pandas as pd
import io
import json
from django.template.loader import render_to_string
from apps.students.services import BulkAdmissionService
from apps.core.bulk_services import BulkFacultyService, BulkCoreService

from apps.faculty.forms import (
    FacultyStep1AccountForm, FacultyStep2ProfessionalForm, FacultyStep3DocumentForm, 
    SubjectAllotmentForm, SubjectScheduleForm, SyllabusTopicForm
)
from apps.faculty.models import FacultyProfile, FacultyDocument
from apps.students.models import Student, Guardian, Document, AdmissionEnquiry, CommunicationTemplate, CommunicationLog

@login_required
def dashboard(request):
    """Main entry point that redirects to the appropriate dashboard based on role."""
    user = request.user
    role = str(user.role).upper()
    
    if role == 'STUDENT':
        return redirect('student_dashboard')
    
    context = {
        'total_students': Student.objects.count(),
        'total_faculty': FacultyProfile.objects.count(),
        'fees_collected': "₹4.2M", 
        'attendance_avg': "92%",
        'recent_activities': [
            {'user': 'Admin', 'action': 'Created new student profile', 'time': '2 mins ago'},
            {'user': 'HOD CS', 'action': 'Updated class timetable', 'time': '15 mins ago'},
        ]
    }

    if role in ['ADMIN', 'SUB_ADMIN']:
        return render(request, 'dashboard/admin_dashboard.html', context)
    
    elif role == 'HOD':
        try:
            hod_dept = user.faculty_profile.department
            context['total_students'] = Student.objects.filter(department=hod_dept).count()
            context['total_faculty'] = FacultyProfile.objects.filter(department=hod_dept).count()
            context['active_courses'] = Subject.objects.filter(branch__program__dept=hod_dept).count()
            
            coverage_data = SyllabusCoverage.objects.filter(allotment__subject__branch__program__dept=hod_dept)
            context['syllabus_avg'] = coverage_data.aggregate(Avg('percentage'))['percentage__avg'] or 0
            context['top_coverage'] = coverage_data.select_related('allotment__subject').order_by('-percentage')[:3]
            
            context['faculty_workload'] = FacultyProfile.objects.filter(department=hod_dept).annotate(
                total_sessions=Count('allotments__schedules')
            ).select_related('user')[:5]
            
            context['critical_alerts'] = HODNotification.objects.filter(
                department=hod_dept, 
                is_active=True,
                priority__in=['high', 'critical']
            )[:3]
            
            research = ResearchPublication.objects.filter(faculty__department=hod_dept)
            context['research_stats'] = {
                'journals': research.filter(pub_type='Journal').count(),
                'conferences': research.filter(pub_type='Conference').count(),
                'patents': research.filter(pub_type='Patent').count(),
                'total_pubs': research.filter(pub_type__in=['Journal', 'Conference']).count()
            }
        except Exception as e:
            print(f"HOD Dashboard Error: {e}")
            pass
        return render(request, 'dashboard/hod_dashboard.html', context)
    
    elif role == 'ACCOUNTANT':
        from django.utils import timezone
        from django.db.models import Sum, OuterRef, Subquery, DecimalField
        from django.db.models.functions import Coalesce
        
        today = timezone.now().date()
        start_of_month = today.replace(day=1)

        today_receipts = FeeReceipt.objects.filter(transaction_date__date=today)
        context['today_revenue'] = today_receipts.aggregate(Sum('amount'))['amount__sum'] or 0
        context['today_receipt_count'] = today_receipts.count()
        
        month_expenses = FinancialExpense.objects.filter(expense_date__gte=start_of_month)
        context['monthly_expenses'] = month_expenses.aggregate(Sum('amount'))['amount__sum'] or 0
        
        context['recent_transactions'] = FeeReceipt.objects.select_related('student__user').order_by('-transaction_date')[:5]

        # Subquery to calculate verified paid receipts per student
        receipts_subquery = FeeReceipt.objects.filter(
            student=OuterRef('pk'),
            is_verified=True
        ).values('student').annotate(
            total=Sum('amount')
        ).values('total')
        
        # Annotate active students with total paid
        active_students = Student.objects.filter(status='active').select_related('user', 'branch__program').annotate(
            total_paid=Coalesce(Subquery(receipts_subquery), 0.0, output_field=DecimalField())
        )
        
        total_pending_dues = 0
        defaulters_count = 0
        high_dues_list = []
        
        for s in active_students:
            total_payable = s.one_time_admission_fee + (s.admission_semester_fee * s.semester)
            pending = max(0, total_payable - s.total_paid)
            if pending > 0:
                total_pending_dues += pending
                defaulters_count += 1
                high_dues_list.append({
                    'student': s,
                    'total_payable': total_payable,
                    'paid': s.total_paid,
                    'pending': pending
                })
        
        # Sort by pending amount descending
        high_dues_list.sort(key=lambda x: x['pending'], reverse=True)
        
        # Format pending dues total for summary card
        if total_pending_dues >= 100000:
            pending_dues_str = f"₹{total_pending_dues / 100000:.1f}L"
        else:
            pending_dues_str = f"₹{total_pending_dues:,.0f}"
            
        context['pending_dues'] = pending_dues_str
        context['defaulters_count'] = defaulters_count
        context['high_dues_list'] = high_dues_list[:5]

        return render(request, 'dashboard/accountant_dashboard.html', context)
    
    elif role == 'ADMISSION':
        from django.utils import timezone
        today = timezone.now().date()

        # 1. Funnel Metrics
        context['total_enquiries'] = AdmissionEnquiry.objects.count()
        context['enquiries_today'] = AdmissionEnquiry.objects.filter(created_at__date=today).count()
        
        context['applications_submitted'] = Student.objects.count()
        context['applications_today'] = Student.objects.filter(created_at__date=today).count()
        
        context['verified_docs'] = Document.objects.filter(verified=True).count()
        context['total_admissions'] = Student.objects.exclude(enrollment_number__isnull=True).exclude(enrollment_number='').count()

        # 2. Recent Applications
        context['recent_applications'] = Student.objects.select_related('user', 'branch__program').order_by('-created_at')[:5]

        # 3. Needs Verification
        context['needs_verification'] = Document.objects.filter(verified=False).select_related('student__user')[:5]
        context['pending_verification_count'] = Document.objects.filter(verified=False).count()

        # 4. Intake Pipeline (Dynamic)
        from apps.core.models import Branch
        branches = Branch.objects.all().annotate(student_count=Count('students'))
        intake_pipeline = []
        for b in branches:
            # Assuming a mock capacity of 60 for calculation if not defined in model
            capacity = 180 if "Computer" in b.branch_name else 60
            percentage = (b.student_count / capacity) * 100 if capacity > 0 else 0
            intake_pipeline.append({
                'name': f"{b.program.program_code} - {b.branch_name}",
                'count': b.student_count,
                'capacity': capacity,
                'percentage': min(percentage, 100)
            })
        context['intake_pipeline'] = intake_pipeline[:2] # Top 2 for the UI

        return render(request, 'dashboard/admission_dashboard.html', context)

    elif role in ['FACULTY', 'TEACHER']:
        try:
            faculty = user.faculty_profile
            import datetime
            today = datetime.datetime.now().weekday() + 1 # 1=Mon, 7=Sun
            
            # 1. Today's Classes
            schedules_today = SubjectSchedule.objects.filter(
                allotment__faculty=faculty,
                day=today
            ).select_related('allotment__subject').order_by('start_time')
            
            context['total_classes_today'] = schedules_today.count()
            context['labs_count'] = schedules_today.filter(session_type='Lab').count()
            context['theory_count'] = schedules_today.filter(session_type='Theory').count()
            
            # 2. Live Timeline
            now_time = datetime.datetime.now().time()
            timeline = []
            for s in schedules_today:
                is_live = s.start_time <= now_time <= s.end_time
                timeline.append({
                    'id': s.id,
                    'start_time': s.start_time.strftime("%I:%M %p"),
                    'subject': s.allotment.subject.subject_name,
                    'subject_code': s.allotment.subject.subject_code,
                    'room': s.room_number or "N/A",
                    'type': s.session_type,
                    'is_live': is_live,
                    'batch': "B1" # Partial mock
                })
            context['live_timeline'] = timeline
            
            # 3. Mentees
            context['mentees_count'] = Student.objects.filter(mentor=user).count()
            
            # 4. Mock Data for premium UI
            context['evaluation_pending'] = 12
            context['leave_balance'] = 8
            context['recent_uploads'] = [
                {'title': 'Unit 3: Neural Networks Notes', 'code': 'CS601', 'size': '1.2 MB', 'time': '2 days ago'}
            ]
            
        except Exception as e:
            print(f"Faculty Dashboard Error: {e}")
            pass
        return render(request, 'dashboard/teacher.html', context)
    
    context['role_display'] = user.get_role_display()
    return render(request, 'dashboard/staff.html', context)


@login_required
def student(request):
    if request.user.role != 'STUDENT':
        return redirect('dashboard')
    
    try:
        student = request.user.student_profile
    except (Student.DoesNotExist, AttributeError):
        student = Student.objects.first()
        if not student:
            messages.error(request, "Student profile not found.")
            return redirect('dashboard')
            
    # Calculate attendance statistics
    from apps.faculty.models import StudentAttendance
    overall_qs = StudentAttendance.objects.filter(student=student)
    overall_total = overall_qs.count()
    if overall_total > 0:
        overall_present = overall_qs.filter(status='P').count()
        overall_attendance_percentage = (overall_present / overall_total * 100)
    else:
        overall_attendance_percentage = 0.0

    # Monthly attendance
    from django.utils import timezone
    today = timezone.now().date()
    current_month_start = today.replace(day=1)
    monthly_qs = overall_qs.filter(date__gte=current_month_start)
    monthly_total = monthly_qs.count()
    if monthly_total > 0:
        monthly_present = monthly_qs.filter(status='P').count()
        monthly_attendance_percentage = (monthly_present / monthly_total * 100)
    else:
        monthly_attendance_percentage = 0.0

    # Calculate CGPA from student profile, assignments, or fallback
    if student.cgpa and student.cgpa > 0:
        cgpa = float(student.cgpa)
    else:
        from apps.students.models import AssignmentSubmission
        submissions = AssignmentSubmission.objects.filter(student=student)
        if submissions.count() > 0:
            total_obtained = sum(sub.points_obtained for sub in submissions if sub.points_obtained is not None)
            total_max = sum(sub.assignment.max_points for sub in submissions if sub.points_obtained is not None)
            if total_max > 0:
                cgpa = round((total_obtained / total_max) * 10, 2)
            else:
                cgpa = 8.5
        else:
            # Stable deterministic CGPA based on roll/enrollment number
            import hashlib
            h_str = student.roll_number or student.enrollment_number or str(student.id)
            val = int(hashlib.md5(h_str.encode()).hexdigest(), 16) % 100 / 100.0
            cgpa = round(7.8 + val * 1.8, 2)

    # Rank in department (stable deterministic based on roll/enrollment number)
    import hashlib
    dept_students_count = Student.objects.filter(department=student.department).count()
    if dept_students_count > 1:
        h_str = student.roll_number or student.enrollment_number or str(student.id)
        rank = (int(hashlib.md5((h_str + "rank").encode()).hexdigest(), 16) % dept_students_count) + 1
    else:
        rank = 12

    # Query learning progress / syllabus coverages & attendance per subject
    from apps.core.models import Subject
    subjects = Subject.objects.filter(branch=student.branch, semester=student.semester)
    learning_progress = []
    
    for subj in subjects:
        # Calculate actual lectures held and attended from StudentAttendance
        subj_attendance = StudentAttendance.objects.filter(student=student, allotment__subject=subj)
        total_lectures = subj_attendance.count()
        attended_lectures = subj_attendance.filter(status='P').count()
        
        if total_lectures > 0:
            completed = attended_lectures
            total = total_lectures
            percentage = int((completed / total) * 100)
        else:
            completed = 0
            total = 0
            percentage = 0
            
        learning_progress.append({
            'subject_name': subj.subject_name,
            'completed': completed,
            'total': total,
            'percentage': percentage,
        })

    # Query notices
    from apps.core.models import PublicNotice
    notices = PublicNotice.objects.filter(is_active=True).order_by('-created_at')[:5]

    # Calculate pending fees using database-backed fields
    from apps.fees.models import FeeReceipt
    from django.db.models import Sum
    paid_amount = FeeReceipt.objects.filter(student=student, is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
    total_fee_due = student.one_time_admission_fee + (student.admission_semester_fee * student.semester)
    pending_fees = max(0, total_fee_due - paid_amount)

    # Calculate overall course package metrics
    total_semesters = (student.branch.duration_years * 2) if (student.branch and student.branch.duration_years) else 8
    total_course_fee = student.one_time_admission_fee + (student.admission_semester_fee * total_semesters)
    paid_percentage = int((paid_amount / total_fee_due) * 100) if total_fee_due > 0 else 0

    # Mid-term marks logic
    from apps.students.models import MidTermMark
    midterm_qs = MidTermMark.objects.filter(student=student).select_related('subject')
    
    midterm_data = {}
    for subj in subjects:
        midterm_data[subj.subject_name] = {
            'subject_code': subj.subject_code,
            'midterm1': None,
            'midterm2': None
        }
        
    for mark in midterm_qs:
        subj_name = mark.subject.subject_name
        if subj_name not in midterm_data:
            midterm_data[subj_name] = {
                'subject_code': mark.subject.subject_code,
                'midterm1': None,
                'midterm2': None
            }
        midterm_data[subj_name][mark.mid_term_type] = {
            'obtained': float(mark.obtained_marks),
            'max': float(mark.max_marks),
            'remarks': mark.remarks
        }

    context = {
        'student': student,
        'attendance_percentage': round(monthly_attendance_percentage, 1),
        'overall_attendance_percentage': round(overall_attendance_percentage, 1),
        'cgpa': cgpa,
        'rank': rank,
        'dept_students_count': dept_students_count or 15,
        'learning_progress': learning_progress,
        'notices': notices,
        'pending_fees': pending_fees,
        'total_fee_due': total_fee_due,
        'paid_amount': paid_amount,
        'paid_percentage': min(100, paid_percentage),
        'total_course_fee': total_course_fee,
        'total_semesters': total_semesters,
        'midterm_data': midterm_data,
    }
    
    return render(request, 'dashboard/student_dashboard.html', context)


@login_required
def admin(request):
    return redirect('dashboard')

@login_required
def toggle_bulk_porter(request):
    """Master Switch for Bulk Porter security."""
    if request.user.role not in ['ADMIN', 'SUB_ADMIN']:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    
    college_id = request.POST.get('college_id')
    current_status = request.POST.get('status') == 'true'
    new_status = not current_status
    
    college = College.objects.get(id=college_id)
    CollegeSettings.objects.update_or_create(
        college=college,
        setting_key='bulk_porter_active',
        defaults={'setting_value': 'true' if new_status else 'false'}
    )
    return JsonResponse({'status': 'success', 'new_status': new_status})

class BulkImportView(RolePermissionMixin, View):
    required_permission = 'can_manage_users'
    template_name = 'dashboard/bulk_import.html'

    IMPORT_REGISTRY = {
        'colleges': {'model': College, 'name': 'Colleges', 'unique_key': 'college_code'},
        'departments': {'model': Department, 'name': 'Departments', 'unique_key': 'dept_code'},
        'programs': {'model': Program, 'name': 'Programs', 'unique_key': 'program_code'},
        'branches': {'model': Branch, 'name': 'Branches', 'unique_key': 'branch_code'},
        'subjects': {'model': Subject, 'name': 'Subjects Master', 'unique_key': 'subject_code'},
        'students': {'model': Student, 'name': 'Student Registry', 'unique_key': 'enrollment_number', 'handler': 'process_students'},
        'bulk_admission': {'model': Student, 'name': 'Bulk Student Admission (Pro)', 'unique_key': 'roll_number', 'handler': 'process_bulk_admission'},
        'faculty': {'model': FacultyProfile, 'name': 'Faculty Pool', 'unique_key': 'employee_id'},
        'bulk_faculty': {'model': FacultyProfile, 'name': 'Bulk Faculty Registration (Pro)', 'unique_key': 'employee_id', 'handler': 'process_bulk_faculty'},
        'bulk_branches': {'model': Branch, 'name': 'Bulk Branch Porter (Pro)', 'unique_key': 'branch_code', 'handler': 'process_bulk_branches'},
        'bulk_study_material': {'model': StudyMaterial, 'name': 'Bulk Study Materials (Pro)', 'unique_key': 'title', 'handler': 'process_bulk_study_material'},
    }

    def is_enabled(self):
        try:
            setting = CollegeSettings.objects.filter(setting_key='bulk_porter_active').first()
            return setting.setting_value == 'true' if setting else False
        except: return False

    def get(self, request):
        enabled = self.is_enabled()
        import_types = [{'id': k, 'name': v['name']} for k, v in self.IMPORT_REGISTRY.items()]
        return render(request, self.template_name, {
            'import_types': import_types,
            'is_enabled': enabled,
            'college': College.objects.first()
        })

    def post(self, request):
        if not self.is_enabled():
            messages.error(request, "Security Lockdown: Bulk Porter is currently disabled.")
            return redirect('bulk_import')

        action = request.POST.get('action') # 'analyze' or 'commit'
        import_type = request.POST.get('import_type')
        mode = request.POST.get('operation_mode', 'sync') # 'add', 'update', 'sync'
        upload_file = request.FILES.get('upload_file')
        
        if not upload_file:
            messages.error(request, "No file provided for porter operation.")
            return redirect('bulk_import')

        try:
            filename = upload_file.name.lower()
            if filename.endswith('.csv'): df = pd.read_csv(upload_file).fillna('')
            elif filename.endswith(('.xlsx', '.xls')): 
                if import_type in ['bulk_admission', 'bulk_faculty']:
                    df = pd.read_excel(upload_file, sheet_name=None)
                else:
                    df = pd.read_excel(upload_file).fillna('')
            elif filename.endswith('.json'): df = pd.read_json(upload_file).fillna('')
            else: raise Exception("Unsupported format")

            config = self.IMPORT_REGISTRY[import_type]
            model = config['model']

            # --- SMART SCHEMA VALIDATION ---
            # 1. Identify all valid field names (including those with _id suffixes)
            all_db_fields = set()
            for f in model._meta.get_fields():
                all_db_fields.add(f.name)
                # Support SQL-style suffixes (like 'branch_id') for ForeignKeys
                if hasattr(f, 'attname'): all_db_fields.add(f.attname)
            
            valid_fields = {f.name for f in model._meta.get_fields() if f.editable}
            valid_fields.add('id')
            # Add attnames (suffixes) to valid_fields too if they are editable
            valid_fields.update({f.attname for f in model._meta.fields if f.editable})

            schema_error = None
            if import_type not in ['bulk_admission', 'bulk_faculty']:
                for index, col in enumerate(df.columns):
                    base_col = col.split('__')[0] if '__' in col else col
                    if base_col not in valid_fields and base_col not in all_db_fields:
                        schema_error = {
                            'column': col,
                            'position': index + 1,
                            'message': f"Column '{col}' is not a valid field for {config['name']}. Please check your spelling or remove it."
                        }
                        break
            
            if schema_error:
                return render(request, self.template_name, {
                    'import_types': [{'id': k, 'name': v['name']} for k, v in self.IMPORT_REGISTRY.items()],
                    'is_enabled': True,
                    'analysis_complete': True,
                    'is_blocked': True,
                    'results': {'schema_error': schema_error},
                    'import_type': import_type,
                    'operation_mode': mode,
                })

            is_dry_run = (action == 'analyze')

            with transaction.atomic():
                if 'handler' in config:
                    handler_func = getattr(self, config['handler'])
                    results = handler_func(df, dry_run=is_dry_run, mode=mode)
                else:
                    results = self.process_universal(config, df, dry_run=is_dry_run, mode=mode)
                
                if is_dry_run:
                    transaction.set_rollback(True)
                    return render(request, self.template_name, {
                        'import_types': [{'id': k, 'name': v['name']} for k, v in self.IMPORT_REGISTRY.items()],
                        'is_enabled': True,
                        'analysis_complete': True,
                        'results': results,
                        'import_type': import_type,
                        'operation_mode': mode,
                        'preview_rows': self.get_preview_rows(df, import_type)
                    })

            messages.success(request, f"Successfully executed Porter operation: {results['success']} records processed.")
            return redirect('bulk_import')

        except Exception as e:
            messages.error(request, f"Porter Security Error: {str(e)}")
            return redirect('bulk_import')

    def get_unique_fields(self, model):
        """Discovers all fields that can uniquely identify a record."""
        return [f.name for f in model._meta.fields if f.unique or f.primary_key]

    def find_lookup_params(self, model, data, registry_key):
        """Identifies the best lookup parameters from CSV data."""
        params = {}
        # 1. Try explicit ID
        if 'id' in data and data['id']:
            return {'id': data['id']}
        
        # 2. Try registry key
        if registry_key in data and data[registry_key]:
            return {registry_key: data[registry_key]}
        
        # 3. Auto-discover from unique model fields
        unique_fields = self.get_unique_fields(model)
        for field in unique_fields:
            if field in data and data[field]:
                return {field: data[field]}
        return None

    def resolve_relational_value(self, model, field_name, value):
        """Intelligently resolves a Foreign Key object from a variety of identifier types."""
        if not value or pd.isna(value): return None
        
        try:
            field = model._meta.get_field(field_name)
            if not field.is_relation: return value
            
            rel_model = field.related_model
            # 1. Try numeric ID if value is digit
            if str(value).isdigit():
                obj = rel_model.objects.filter(id=value).first()
                if obj: return obj
            
            # 2. Try all unique fields of the related model
            rel_uniques = self.get_unique_fields(rel_model)
            for r_field in rel_uniques:
                obj = rel_model.objects.filter(**{r_field: value}).first()
                if obj: return obj
                
            raise ValidationError(f"Could not resolve {field_name} '{value}'")
        except: raise

    def process_universal(self, config, df, dry_run=False, mode='sync'):
        model = config['model']
        lookup_key = config['unique_key']
        res = {'success': 0, 'new': 0, 'updated': 0, 'errors': [], 'new_rows': [], 'update_rows': []}

        for index, row in df.iterrows():
            try:
                data = row.to_dict()
                lookup_params = self.find_lookup_params(model, data, lookup_key)
                
                if not lookup_params:
                    res['errors'].append(f"Row {index+1}: No unique identifier found (ID or {lookup_key} missing)"); continue

                existing_obj = model.objects.filter(**lookup_params).first()

                # Operation Mode Enforcements
                if mode == 'add' and existing_obj:
                    res['errors'].append(f"Row {index+1}: Record exists (Add-Only failure)"); continue
                if mode == 'update' and not existing_obj:
                    res['errors'].append(f"Row {index+1}: Not found (Update-Only failure)"); continue

                diffs = []
                field_values = {}
                
                # Intelligent Attribute Mapping & Relational Resolution
                for col, val in data.items():
                    if col in ['id'] or col in lookup_params: continue
                    
                    try:
                        clean_val = str(val).strip() if pd.notna(val) else ""
                        
                        # Handle Explicit Lookup (field__key)
                        if '__' in col:
                            f_name, l_field = col.split('__')
                            rel_field = model._meta.get_field(f_name)
                            rel_obj = rel_field.related_model.objects.filter(**{l_field: val}).first()
                            
                            if rel_obj:
                                field_values[f_name] = rel_obj
                                if existing_obj:
                                    curr = getattr(existing_obj, f_name)
                                    if curr != rel_obj:
                                        diffs.append({'field': f_name.title(), 'old': str(curr), 'new': str(rel_obj)})
                            elif clean_val: raise ValidationError(f"Missing {f_name} '{val}'")
                            
                        # Handle Smart Discovery (field)
                        else:
                            field_meta = model._meta.get_field(col)
                            if field_meta.is_relation:
                                resolved_obj = self.resolve_relational_value(model, col, val)
                                field_values[col] = resolved_obj
                                if existing_obj:
                                    curr = getattr(existing_obj, col)
                                    if curr != resolved_obj:
                                        diffs.append({'field': col.title(), 'old': str(curr), 'new': str(resolved_obj)})
                            else:
                                if not clean_val and not existing_obj: continue 
                                field_values[col] = val
                                if existing_obj:
                                    curr = getattr(existing_obj, col)
                                    curr_clean = str(curr).strip() if curr is not None else ""
                                    if curr_clean != clean_val:
                                        diffs.append({
                                            'field': col.replace('_', ' ').title(),
                                            'old': curr_clean or "(Empty)",
                                            'new': clean_val or "(Clear)"
                                        })
                    except Exception as e: continue

                if not dry_run:
                    model.objects.update_or_create(**lookup_params, defaults=field_values)
                
                if existing_obj:
                    res['updated'] += 1
                    if diffs and len(res['update_rows']) < 50:
                        res['update_rows'].append({'identity': str(existing_obj), 'diffs': diffs})
                else:
                    res['new'] += 1
                    if len(res['new_rows']) < 50:
                        res['new_rows'].append({k: v for k, v in data.items() if k not in ['id']})
                res['success'] += 1
            except Exception as e:
                res['errors'].append(f"Row {index+1}: {str(e)}")
        return res

    def process_students(self, df, dry_run=False, mode='sync'):
        res = {'success': 0, 'new': 0, 'updated': 0, 'errors': [], 'new_rows': [], 'update_rows': []}
        from apps.accounts.models import Role
        student_role = Role.objects.get(role_name='STUDENT')

        for index, row in df.iterrows():
            try:
                data = row.to_dict()
                enrollment = str(data.get('enrollment_number', '')).strip()
                email = str(data.get('email', '')).strip()
                if not enrollment or not email: res['errors'].append(f"Row {index+1}: Roll/Email missing"); continue

                existing_student = Student.objects.filter(enrollment_number=enrollment).first()
                if mode == 'add' and existing_student: res['errors'].append(f"Row {index+1}: Student exists"); continue
                if mode == 'update' and not existing_student: res['errors'].append(f"Row {index+1}: Not found"); continue

                diffs = []
                if existing_student:
                    if str(data.get('email')) != existing_student.user.email:
                        diffs.append({'field': 'Email', 'old': existing_student.user.email, 'new': data.get('email')})
                    if str(data.get('section')) != existing_student.section:
                        diffs.append({'field': 'Section', 'old': existing_student.section, 'new': data.get('section')})

                if not dry_run:
                    branch_code = data.get('branch__branch_code')
                    branch = Branch.objects.filter(branch_code=branch_code).first()
                    user, _ = User.objects.update_or_create(email=email, defaults={'username': enrollment, 'role': student_role})
                    user.set_password('Welcome@123'); user.save()
                    Student.objects.update_or_create(user=user, defaults={'enrollment_number': enrollment, 'branch': branch, 'status': 'active'})
                
                if existing_student:
                    res['updated'] += 1
                    if diffs and len(res['update_rows']) < 50:
                        res['update_rows'].append({
                            'identity': enrollment, 
                            'diffs': diffs
                        })
                else:
                    res['new'] += 1
                    if len(res['new_rows']) < 50:
                        res['new_rows'].append({k: v for k, v in data.items() if k not in ['id']})
                res['success'] += 1
            except Exception as e:
                res['errors'].append(f"Row {index+1}: {str(e)}")
        return res

    def process_bulk_admission(self, dfs, dry_run=False, mode='sync'):
        """Calls the BulkAdmissionService to handle multi-sheet student/user creation."""
        results = BulkAdmissionService.execute_import(
            dfs, 
            dry_run=dry_run, 
            update_existing=(mode == 'sync' or mode == 'update')
        )
        
        # Adapt service results to View's report format
        report = {
            'success': results['inserted'],
            'new': results['inserted'], 
            'updated': results['updated'],
            'errors': [f"{e['sheet']} Row {e['row']}: {e['message']}" for e in results['errors']],
            'new_rows_users': dfs.get('users').head(5).to_dict('records') if results['inserted'] > 0 else [],
            'new_rows_students': dfs.get('students').head(5).to_dict('records') if results['inserted'] > 0 else [],
            'new_rows': [], # Placeholder for single-table compatibility
            'update_rows': []
        }
        return report

    def get_preview_rows(self, df, import_type):
        """Helper to get preview rows based on import type."""
        if import_type == 'bulk_admission': return df.get('students').head(5).to_dict('records')
        if import_type == 'bulk_faculty': return df.get('faculty').head(5).to_dict('records')
        if isinstance(df, dict): return [] # Should not happen for others
        return df.head(5).to_dict('records')

    def process_bulk_faculty(self, dfs, dry_run=False, mode='sync'):
        results = BulkFacultyService.execute_import(dfs, dry_run=dry_run, update_existing=(mode == 'sync'))
        return {
            'success': results['inserted'], 'new': results['inserted'], 'updated': results['updated'],
            'errors': [f"{e['sheet']} Row {e['row']}: {e['message']}" for e in results['errors']],
            'new_rows_users': dfs.get('users').head(5).to_dict('records') if results['inserted'] > 0 else [],
            'new_rows_faculty': dfs.get('faculty').head(5).to_dict('records') if results['inserted'] > 0 else [],
            'new_rows': []
        }

    def process_bulk_branches(self, df, dry_run=False, mode='sync'):
        results = BulkCoreService.import_branches(df, dry_run=dry_run)
        return {
            'success': results['inserted'], 'new': results['inserted'], 'updated': 0,
            'errors': [f"Row {e['row']}: {e['message']}" for e in results['errors']],
            'new_rows': df.head(10).to_dict('records') if results['inserted'] > 0 else []
        }

    def process_bulk_study_material(self, df, dry_run=False, mode='sync'):
        results = BulkCoreService.import_study_material(df, dry_run=dry_run)
        return {
            'success': results['inserted'], 'new': results['inserted'], 'updated': 0,
            'errors': [f"Row {e['row']}: {e['message']}" for e in results['errors']],
            'new_rows': df.head(10).to_dict('records') if results['inserted'] > 0 else []
        }

@login_required
def teacher(request):
    return render(request, 'dashboard/teacher.html')



# --- STUDENT MODULE ---
# Note: Redundant StudentListView and StudentCreateView removed in favor of Consolidated Registry views below.



# --- STAFF PROFILE MODULE ---
class StaffProfileListView(RolePermissionMixin, ERPListView):
    model = StaffProfile
    module_name = "Staff"
    list_fields = ['employee_id', 'user', 'department']
    required_permission = 'can_manage_users'

class StaffProfileCreateView(ERPCreateView):
    model = StaffProfile
    module_name = "Staff"
    fields = ['user', 'employee_id', 'department']
    success_url = reverse_lazy('staff_list')

class StaffProfileUpdateView(ERPUpdateView):
    model = StaffProfile
    module_name = "Staff"
    fields = ['user', 'employee_id', 'department']
    success_url = reverse_lazy('staff_list')

class StaffProfileDetailView(RolePermissionMixin, ERPDetailView):
    model = StaffProfile
    module_name = "Staff"
    required_permission = 'can_manage_users'

# --- ID COUNTER (Admin-only) ---
class IDCounterListView(RolePermissionMixin, ERPListView):
    model = IDCounter
    module_name = "ID Sequence"
    list_fields = ['prefix', 'last_serial']
    required_permission = 'can_manage_users'

class IDCounterDetailView(RolePermissionMixin, ERPDetailView):
    model = IDCounter
    module_name = "ID Sequence"
    detail_fields = ['prefix', 'last_serial']
    required_permission = 'can_manage_users'

class IDCounterCreateView(ERPCreateView):
    model = IDCounter
    module_name = "ID Sequence"
    fields = ['prefix', 'last_serial']
    success_url = reverse_lazy('id_counter_list')

class IDCounterUpdateView(ERPUpdateView):
    model = IDCounter
    module_name = "ID Sequence"
    fields = ['prefix', 'last_serial']
    success_url = reverse_lazy('id_counter_list')

# --- ACADEMIC HIERARCHY MODULES ---

# 1. College
class CollegeListView(RolePermissionMixin, ERPListView):
    model = College
    module_name = "College"
    list_fields = ['name', 'college_code', 'website']
    required_permission = 'can_manage_users'

class CollegeDetailView(RolePermissionMixin, ERPDetailView):
    model = College
    module_name = "College"
    required_permission = 'can_manage_users'

class CollegeCreateView(ERPCreateView):
    model = College
    module_name = "College"
    fields = ['name', 'college_code', 'address', 'website']
    success_url = reverse_lazy('college_list')

class CollegeUpdateView(ERPUpdateView):
    model = College
    module_name = "College"
    fields = ['name', 'college_code', 'address', 'website']
    success_url = reverse_lazy('college_list')

# 2. Department
class DepartmentListView(RolePermissionMixin, ERPListView):
    model = Department
    module_name = "Department"
    list_fields = ['dept_name', 'dept_code', 'college']
    required_permission = 'can_view_academic_registry'

class DepartmentDetailView(RolePermissionMixin, ERPDetailView):
    model = Department
    module_name = "Department"
    required_permission = 'can_view_academic_registry'

class DepartmentCreateView(ERPCreateView):
    model = Department
    module_name = "Department"
    fields = ['college', 'dept_name', 'dept_code']
    success_url = reverse_lazy('department_list')

class DepartmentUpdateView(ERPUpdateView):
    model = Department
    module_name = "Department"
    fields = ['college', 'dept_name', 'dept_code']
    success_url = reverse_lazy('department_list')

# 3. Programs
class ProgramListView(RolePermissionMixin, ERPListView):
    model = Program
    module_name = "Program"
    list_fields = ['program_name', 'program_code', 'dept']
    required_permission = 'can_manage_users'

class ProgramDetailView(RolePermissionMixin, ERPDetailView):
    model = Program
    module_name = "Program"
    required_permission = 'can_manage_users'

class ProgramCreateView(ERPCreateView):
    model = Program
    module_name = "Program"
    fields = ['dept', 'program_name', 'program_code']
    success_url = reverse_lazy('program_list')

class ProgramUpdateView(ERPUpdateView):
    model = Program
    module_name = "Program"
    fields = ['dept', 'program_name', 'program_code']
    success_url = reverse_lazy('program_list')

# 4. Branch
class BranchListView(RolePermissionMixin, ERPListView):
    model = Branch
    module_name = "Branch"
    list_fields = ['branch_name', 'branch_code', 'program', 'duration_years']
    required_permission = 'can_view_academic_registry'

class BranchDetailView(RolePermissionMixin, ERPDetailView):
    model = Branch
    module_name = "Branch"
    required_permission = 'can_manage_users'

class BranchCreateView(ERPCreateView):
    model = Branch
    module_name = "Branch"
    fields = ['program', 'branch_name', 'branch_code', 'duration_years']
    success_url = reverse_lazy('branch_list')

class BranchUpdateView(ERPUpdateView):
    model = Branch
    module_name = "Branch"
    fields = ['program', 'branch_name', 'branch_code', 'duration_years']
    success_url = reverse_lazy('branch_list')

# --- SUBJECT MANAGEMENT ---
class SubjectListView(RolePermissionMixin, ERPListView):
    model = Subject
    module_name = "Subject"
    list_fields = ['subject_name', 'subject_code', 'subject_type', 'credits', 'semester', 'branch']
    required_permission = 'can_view_subjects'

class SubjectCreateView(RolePermissionMixin, ERPCreateView):
    model = Subject
    module_name = "Subject"
    form_class = SubjectForm
    success_url = reverse_lazy('subject_list')
    required_permission = 'can_manage_subjects'

class SubjectUpdateView(RolePermissionMixin, ERPUpdateView):
    model = Subject
    module_name = "Subject"
    form_class = SubjectForm
    success_url = reverse_lazy('subject_list')
    required_permission = 'can_manage_subjects'

class SubjectDetailView(RolePermissionMixin, ERPDetailView):
    model = Subject
    module_name = "Subject"
    required_permission = 'can_view_subjects'

class SubjectDeleteView(RolePermissionMixin, View):
    required_permission = 'can_manage_subjects'
    def post(self, request, pk):
        subject = Subject.objects.get(pk=pk)
        subject.delete()
        messages.success(request, "Subject deleted successfully")
        return redirect('subject_list')

# 4. College Settings
class CollegeSettingsListView(RolePermissionMixin, ERPListView):
    model = CollegeSettings
    module_name = "Institutional Setting"
    list_fields = ['college', 'setting_key', 'setting_value']
    required_permission = 'can_manage_users'

class CollegeSettingsDetailView(RolePermissionMixin, ERPDetailView):
    model = CollegeSettings
    module_name = "Institutional Setting"
    required_permission = 'can_manage_users'

class CollegeSettingsCreateView(ERPCreateView):
    model = CollegeSettings
    module_name = "Institutional Setting"
    fields = ['college', 'setting_key', 'setting_value']
    success_url = reverse_lazy('college_settings_list')

class CollegeSettingsUpdateView(ERPUpdateView):
    model = CollegeSettings
    module_name = "Institutional Setting"
    fields = ['college', 'setting_key', 'setting_value']
    success_url = reverse_lazy('college_settings_list')

class BulkOutreachView(RolePermissionMixin, View):
    required_permission = 'can_manage_students'
    template_name = 'dashboard/bulk_outreach.html'

    def get(self, request, *args, **kwargs):
        from apps.core.models import Program
        
        # 1. Prepare Filter Data
        context = {
            'module_name': "Bulk Outreach Centre",
            'programs': Program.objects.all(),
            'enquiry_statuses': [s[0] for s in AdmissionEnquiry.STATUS_CHOICES],
            'templates': CommunicationTemplate.objects.all().order_by('-created_at'),
            # Stats for last 30 days
            'total_sent': CommunicationLog.objects.filter(status='Sent').count(),
            'recent_logs': CommunicationLog.objects.all()[:10]
        }
        
        # 2. AJAX Recipient Count Preview
        if request.GET.get('action') == 'get_count':
            count = self.get_filtered_recipients(request).count()
            return JsonResponse({'count': count})

        return render(request, self.template_name, context)

    def get_filtered_recipients(self, request):
        program_id = request.GET.get('program')
        status = request.GET.get('status')
        source = request.GET.get('source')
        audience = request.GET.get('audience', 'enquiry')

        if audience == 'student':
            qs = Student.objects.filter(status='active')
            if program_id: qs = qs.filter(program_id=program_id)
        else:
            qs = AdmissionEnquiry.objects.all()
            if program_id: qs = qs.filter(course_interested_id=program_id)
            if status: qs = qs.filter(status=status)
            if source: qs = qs.filter(source=source)
            
        return qs

    def post(self, request, *args, **kwargs):
        # 1. Extract form data
        channel = request.POST.get('channel', 'Email')
        subject = request.POST.get('subject', '')
        message_body = request.POST.get('body', '')
        
        # 2. Get recipients (manually reconstruct filters from POST)
        program_id = request.POST.get('program')
        status = request.POST.get('status')
        audience = request.POST.get('audience', 'enquiry')
        
        if audience == 'student':
            recipients = Student.objects.filter(status='active')
            if program_id: recipients = recipients.filter(program_id=program_id)
        else:
            recipients = AdmissionEnquiry.objects.all()
            if program_id: recipients = recipients.filter(course_interested_id=program_id)
            if status: recipients = recipients.filter(status=status)

        if not recipients.exists():
            messages.warning(request, "No recipients found for the selected filters.")
            return redirect('bulk_outreach')

        # 3. Mass Send Log Logic
        count_success = 0
        with transaction.atomic():
            for r in recipients:
                # Personalization
                name = r.name if hasattr(r, 'name') else r.user.get_full_name()
                personal_body = message_body.replace('{{name}}', name)
                
                # Contact details
                contact = r.phone if channel != 'Email' else r.email
                if not contact: continue

                # Create Log (The "Mock" sending part)
                CommunicationLog.objects.create(
                    sender=request.user,
                    recipient_name=name,
                    recipient_contact=contact,
                    channel=channel,
                    subject=subject if channel == 'Email' else None,
                    body=personal_body,
                    status='Sent'
                )
                count_success += 1

        messages.success(request, f"Bulk Outreach Successful! Sent {count_success} messages via {channel}.")
        return redirect('bulk_outreach')


# ==========================================
# WEBSITE CMS MANAGEMENT MODULES
# ==========================================
from django.contrib.auth.mixins import UserPassesTestMixin

class CMSAdminRequiredMixin(UserPassesTestMixin):
    """Restricts access to only ADMIN, SUB_ADMIN, or Superusers."""
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        return self.request.user.is_superuser or str(self.request.user.role).upper() in ['ADMIN', 'SUB_ADMIN']

    def handle_no_permission(self):
        messages.error(self.request, "Access Denied: You do not have permission to manage website content.")
        return redirect('dashboard')

class BaseCMSListView(CMSAdminRequiredMixin, ERPListView):
    """Base List View for CMS models that ensures can_add and can_edit are True."""
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_add'] = True
        context['can_edit'] = True
        return context

class CMSDeleteView(CMSAdminRequiredMixin, View):
    """Generic Delete View for CMS models that handles both GET and POST."""
    model = None
    success_url = None

    def get(self, request, pk):
        try:
            obj = self.model.objects.get(pk=pk)
            obj.delete()
            messages.success(request, f"{self.model.__name__} deleted successfully.")
        except self.model.DoesNotExist:
            messages.error(request, "Record not found.")
        return redirect(self.success_url)

    def post(self, request, pk):
        try:
            obj = self.model.objects.get(pk=pk)
            obj.delete()
            messages.success(request, f"{self.model.__name__} deleted successfully.")
        except self.model.DoesNotExist:
            messages.error(request, "Record not found.")
        return redirect(self.success_url)


# 1. Hero Slide Views
class HeroSlideListView(BaseCMSListView):
    model = HeroSlide
    module_name = "Hero Slide"
    list_fields = ['title', 'order', 'is_active']

class HeroSlideDetailView(CMSAdminRequiredMixin, ERPDetailView):
    model = HeroSlide
    module_name = "Hero Slide"

class HeroSlideCreateView(CMSAdminRequiredMixin, ERPCreateView):
    model = HeroSlide
    module_name = "Hero Slide"
    fields = ['title', 'subtitle', 'image_url', 'image', 'button_text', 'button_url', 'order', 'is_active']
    success_url = reverse_lazy('cms_heroslide_list')

class HeroSlideUpdateView(CMSAdminRequiredMixin, ERPUpdateView):
    model = HeroSlide
    module_name = "Hero Slide"
    fields = ['title', 'subtitle', 'image_url', 'image', 'button_text', 'button_url', 'order', 'is_active']
    success_url = reverse_lazy('cms_heroslide_list')

class HeroSlideDeleteView(CMSDeleteView):
    model = HeroSlide
    success_url = reverse_lazy('cms_heroslide_list')


# 2. Public Notice Views
class PublicNoticeListView(BaseCMSListView):
    model = PublicNotice
    module_name = "Public Notice"
    list_fields = ['title', 'notice_type', 'is_popup', 'is_active', 'created_at']

class PublicNoticeDetailView(CMSAdminRequiredMixin, ERPDetailView):
    model = PublicNotice
    module_name = "Public Notice"

class PublicNoticeCreateView(CMSAdminRequiredMixin, ERPCreateView):
    model = PublicNotice
    module_name = "Public Notice"
    fields = ['title', 'content', 'notice_type', 'link_url', 'is_popup', 'is_active']
    success_url = reverse_lazy('cms_publicnotice_list')

class PublicNoticeUpdateView(CMSAdminRequiredMixin, ERPUpdateView):
    model = PublicNotice
    module_name = "Public Notice"
    fields = ['title', 'content', 'notice_type', 'link_url', 'is_popup', 'is_active']
    success_url = reverse_lazy('cms_publicnotice_list')

class PublicNoticeDeleteView(CMSDeleteView):
    model = PublicNotice
    success_url = reverse_lazy('cms_publicnotice_list')


# 3. College Event Views
class CollegeEventListView(BaseCMSListView):
    model = CollegeEvent
    module_name = "College Event"
    list_fields = ['title', 'event_date', 'venue', 'is_active']

class CollegeEventDetailView(CMSAdminRequiredMixin, ERPDetailView):
    model = CollegeEvent
    module_name = "College Event"

class CollegeEventCreateView(CMSAdminRequiredMixin, ERPCreateView):
    model = CollegeEvent
    module_name = "College Event"
    fields = ['title', 'event_date', 'venue', 'image_url', 'image', 'link_url', 'is_active']
    success_url = reverse_lazy('cms_collegeevent_list')

class CollegeEventUpdateView(CMSAdminRequiredMixin, ERPUpdateView):
    model = CollegeEvent
    module_name = "College Event"
    fields = ['title', 'event_date', 'venue', 'image_url', 'image', 'link_url', 'is_active']
    success_url = reverse_lazy('cms_collegeevent_list')

class CollegeEventDeleteView(CMSDeleteView):
    model = CollegeEvent
    success_url = reverse_lazy('cms_collegeevent_list')


# 4. Home Program Views
class HomeProgramListView(BaseCMSListView):
    model = HomeProgram
    module_name = "Home Program"
    list_fields = ['title', 'order', 'is_active']

class HomeProgramDetailView(CMSAdminRequiredMixin, ERPDetailView):
    model = HomeProgram
    module_name = "Home Program"

class HomeProgramCreateView(CMSAdminRequiredMixin, ERPCreateView):
    model = HomeProgram
    module_name = "Home Program"
    fields = ['title', 'description', 'image_url', 'image', 'icon_class', 'link_url', 'order', 'is_active']
    success_url = reverse_lazy('cms_homeprogram_list')

class HomeProgramUpdateView(CMSAdminRequiredMixin, ERPUpdateView):
    model = HomeProgram
    module_name = "Home Program"
    fields = ['title', 'description', 'image_url', 'image', 'icon_class', 'link_url', 'order', 'is_active']
    success_url = reverse_lazy('cms_homeprogram_list')

class HomeProgramDeleteView(CMSDeleteView):
    model = HomeProgram
    success_url = reverse_lazy('cms_homeprogram_list')


# 5. Campus Gallery Views
class GalleryItemListView(BaseCMSListView):
    model = GalleryItem
    module_name = "Campus Gallery"
    list_fields = ['title', 'order', 'is_active', 'created_at']

class GalleryItemDetailView(CMSAdminRequiredMixin, ERPDetailView):
    model = GalleryItem
    module_name = "Campus Gallery"

class GalleryItemCreateView(CMSAdminRequiredMixin, ERPCreateView):
    model = GalleryItem
    module_name = "Campus Gallery"
    fields = ['title', 'image_url', 'image', 'order', 'is_active']
    success_url = reverse_lazy('cms_galleryitem_list')

class GalleryItemUpdateView(CMSAdminRequiredMixin, ERPUpdateView):
    model = GalleryItem
    module_name = "Campus Gallery"
    fields = ['title', 'image_url', 'image', 'order', 'is_active']
    success_url = reverse_lazy('cms_galleryitem_list')

class GalleryItemDeleteView(CMSDeleteView):
    model = GalleryItem
    success_url = reverse_lazy('cms_galleryitem_list')


# 6. Recruiter Views
class RecruiterListView(BaseCMSListView):
    model = Recruiter
    module_name = "Recruiter"
    list_fields = ['name', 'order', 'is_active']

class RecruiterDetailView(CMSAdminRequiredMixin, ERPDetailView):
    model = Recruiter
    module_name = "Recruiter"

class RecruiterCreateView(CMSAdminRequiredMixin, ERPCreateView):
    model = Recruiter
    module_name = "Recruiter"
    fields = ['name', 'logo_url', 'logo', 'icon_class', 'order', 'is_active']
    success_url = reverse_lazy('cms_recruiter_list')

class RecruiterUpdateView(CMSAdminRequiredMixin, ERPUpdateView):
    model = Recruiter
    module_name = "Recruiter"
    fields = ['name', 'logo_url', 'logo', 'icon_class', 'order', 'is_active']
    success_url = reverse_lazy('cms_recruiter_list')

class RecruiterDeleteView(CMSDeleteView):
    model = Recruiter
    success_url = reverse_lazy('cms_recruiter_list')


# 7. College Stat Views
class CollegeStatListView(BaseCMSListView):
    model = CollegeStat
    module_name = "College Stat"
    list_fields = ['value', 'label', 'order', 'is_active']

class CollegeStatDetailView(CMSAdminRequiredMixin, ERPDetailView):
    model = CollegeStat
    module_name = "College Stat"

class CollegeStatCreateView(CMSAdminRequiredMixin, ERPCreateView):
    model = CollegeStat
    module_name = "College Stat"
    fields = ['value', 'label', 'order', 'is_active']
    success_url = reverse_lazy('cms_collegestat_list')

class CollegeStatUpdateView(CMSAdminRequiredMixin, ERPUpdateView):
    model = CollegeStat
    module_name = "College Stat"
    fields = ['value', 'label', 'order', 'is_active']
    success_url = reverse_lazy('cms_collegestat_list')

class CollegeStatDeleteView(CMSDeleteView):
    model = CollegeStat
    success_url = reverse_lazy('cms_collegestat_list')


# 8. About Section Config Views
class AboutSectionConfigListView(BaseCMSListView):
    model = AboutSectionConfig
    module_name = "About Config"
    list_fields = ['title', 'director_name', 'is_active']

class AboutSectionConfigDetailView(CMSAdminRequiredMixin, ERPDetailView):
    model = AboutSectionConfig
    module_name = "About Config"

class AboutSectionConfigCreateView(CMSAdminRequiredMixin, ERPCreateView):
    model = AboutSectionConfig
    module_name = "About Config"
    fields = ['title', 'subtitle', 'description_1', 'description_2', 'main_image_url', 'main_image', 'overlap_image_url', 'overlap_image', 'director_name', 'director_designation', 'director_photo_url', 'director_photo', 'director_message', 'button_text', 'button_url', 'is_active']
    success_url = reverse_lazy('cms_aboutsectionconfig_list')

class AboutSectionConfigUpdateView(CMSAdminRequiredMixin, ERPUpdateView):
    model = AboutSectionConfig
    module_name = "About Config"
    fields = ['title', 'subtitle', 'description_1', 'description_2', 'main_image_url', 'main_image', 'overlap_image_url', 'overlap_image', 'director_name', 'director_designation', 'director_photo_url', 'director_photo', 'director_message', 'button_text', 'button_url', 'is_active']
    success_url = reverse_lazy('cms_aboutsectionconfig_list')

class AboutSectionConfigDeleteView(CMSDeleteView):
    model = AboutSectionConfig
    success_url = reverse_lazy('cms_aboutsectionconfig_list')


# 9. Placement Config Views
class PlacementConfigListView(BaseCMSListView):
    model = PlacementConfig
    module_name = "Placement Config"
    list_fields = ['banner_title', 'highest_package', 'average_package', 'is_active']

class PlacementConfigDetailView(CMSAdminRequiredMixin, ERPDetailView):
    model = PlacementConfig
    module_name = "Placement Config"

class PlacementConfigCreateView(CMSAdminRequiredMixin, ERPCreateView):
    model = PlacementConfig
    module_name = "Placement Config"
    fields = ['banner_title', 'banner_subtitle', 'highest_package', 'highest_package_company', 'average_package', 'average_package_batch', 'total_offers', 'total_offers_label', 'total_recruiters', 'total_recruiters_label', 'training_title', 'training_description', 'is_active']
    success_url = reverse_lazy('cms_placementconfig_list')

class PlacementConfigUpdateView(CMSAdminRequiredMixin, ERPUpdateView):
    model = PlacementConfig
    module_name = "Placement Config"
    fields = ['banner_title', 'banner_subtitle', 'highest_package', 'highest_package_company', 'average_package', 'average_package_batch', 'total_offers', 'total_offers_label', 'total_recruiters', 'total_recruiters_label', 'training_title', 'training_description', 'is_active']
    success_url = reverse_lazy('cms_placementconfig_list')

class PlacementConfigDeleteView(CMSDeleteView):
    model = PlacementConfig
    success_url = reverse_lazy('cms_placementconfig_list')


# 10. Placement Achiever Views
class PlacementAchieverListView(BaseCMSListView):
    model = PlacementAchiever
    module_name = "Placement Achiever"
    list_fields = ['student_name', 'company_name', 'package', 'placed_year', 'is_highest', 'is_active']

class PlacementAchieverDetailView(CMSAdminRequiredMixin, ERPDetailView):
    model = PlacementAchiever
    module_name = "Placement Achiever"

class PlacementAchieverCreateView(CMSAdminRequiredMixin, ERPCreateView):
    model = PlacementAchiever
    module_name = "Placement Achiever"
    fields = ['student_name', 'company_name', 'package', 'branch', 'image_url', 'image', 'placed_year', 'is_highest', 'order', 'is_active']
    success_url = reverse_lazy('cms_placementachiever_list')

class PlacementAchieverUpdateView(CMSAdminRequiredMixin, ERPUpdateView):
    model = PlacementAchiever
    module_name = "Placement Achiever"
    fields = ['student_name', 'company_name', 'package', 'branch', 'image_url', 'image', 'placed_year', 'is_highest', 'order', 'is_active']
    success_url = reverse_lazy('cms_placementachiever_list')

class PlacementAchieverDeleteView(CMSDeleteView):
    model = PlacementAchiever
    success_url = reverse_lazy('cms_placementachiever_list')


# 11. Placement Training Feature Views
class PlacementTrainingFeatureListView(BaseCMSListView):
    model = PlacementTrainingFeature
    module_name = "Training Feature"
    list_fields = ['title', 'order', 'is_active']

class PlacementTrainingFeatureDetailView(CMSAdminRequiredMixin, ERPDetailView):
    model = PlacementTrainingFeature
    module_name = "Training Feature"

class PlacementTrainingFeatureCreateView(CMSAdminRequiredMixin, ERPCreateView):
    model = PlacementTrainingFeature
    module_name = "Training Feature"
    fields = ['title', 'order', 'is_active']
    success_url = reverse_lazy('cms_placementtrainingfeature_list')

class PlacementTrainingFeatureUpdateView(CMSAdminRequiredMixin, ERPUpdateView):
    model = PlacementTrainingFeature
    module_name = "Training Feature"
    fields = ['title', 'order', 'is_active']
    success_url = reverse_lazy('cms_placementtrainingfeature_list')

class PlacementTrainingFeatureDeleteView(CMSDeleteView):
    model = PlacementTrainingFeature
    success_url = reverse_lazy('cms_placementtrainingfeature_list')


# 12. Placement Process Step Views
class PlacementProcessStepListView(BaseCMSListView):
    model = PlacementProcessStep
    module_name = "Placement Step"
    list_fields = ['step_number', 'title', 'is_active']

class PlacementProcessStepDetailView(CMSAdminRequiredMixin, ERPDetailView):
    model = PlacementProcessStep
    module_name = "Placement Step"

class PlacementProcessStepCreateView(CMSAdminRequiredMixin, ERPCreateView):
    model = PlacementProcessStep
    module_name = "Placement Step"
    fields = ['step_number', 'title', 'description', 'is_active']
    success_url = reverse_lazy('cms_placementprocessstep_list')

class PlacementProcessStepUpdateView(CMSAdminRequiredMixin, ERPUpdateView):
    model = PlacementProcessStep
    module_name = "Placement Step"
    fields = ['step_number', 'title', 'description', 'is_active']
    success_url = reverse_lazy('cms_placementprocessstep_list')

class PlacementProcessStepDeleteView(CMSDeleteView):
    model = PlacementProcessStep
    success_url = reverse_lazy('cms_placementprocessstep_list')


# ==========================================
# DYNAMIC GENERIC MODEL REGISTRY VIEWS
# ==========================================
from django.apps import apps
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied

GENERIC_MODELS_MAP = {
    'examschedule': ('core', 'ExamSchedule'),
    'guardian': ('students', 'Guardian'),
    'communicationtemplate': ('students', 'CommunicationTemplate'),
    'communicationlog': ('students', 'CommunicationLog'),
    'studentleave': ('students', 'StudentLeave'),
    'assignmentsubmission': ('students', 'AssignmentSubmission'),
    'project': ('students', 'Project'),
    'projectmember': ('students', 'ProjectMember'),
    'projectweeklylog': ('students', 'ProjectWeeklyLog'),
    'projectdeliverable': ('students', 'ProjectDeliverable'),
    'facultydocument': ('faculty', 'FacultyDocument'),
    'subjectschedule': ('faculty', 'SubjectSchedule'),
    'studentattendance': ('faculty', 'StudentAttendance'),
    'assignment': ('faculty', 'Assignment'),
    'facultyleavebalance': ('faculty', 'FacultyLeaveBalance'),
    'facultyleave': ('faculty', 'FacultyLeave'),
    'studymaterial': ('core', 'StudyMaterial'),
}

class GenericModelSetupMixin:
    """Dynamically sets up the target model based on URL parameter."""
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        model_key = self.kwargs.get('model_name')
        if model_key in GENERIC_MODELS_MAP:
            app_label, model_name = GENERIC_MODELS_MAP[model_key]
            self.model = apps.get_model(app_label, model_name)
            self.module_name = self.model._meta.verbose_name.title()
            
            # Dynamically determine list display fields
            self.list_fields = []
            for field in self.model._meta.fields:
                if field.name in ['id', 'created_at', 'updated_at']:
                    continue
                self.list_fields.append(field.name)
            # Limit list fields to 6 for clean table presentation
            self.list_fields = self.list_fields[:6]
        else:
            from django.http import Http404
            raise Http404("Model not found in generic registry")

    def get_success_url(self):
        from django.urls import reverse
        return reverse('generic_model_list', kwargs={'model_name': self.kwargs['model_name']})

    def get_form_class(self):
        from django import forms
        request_obj = self.request
        class DynamicModelForm(forms.ModelForm):
            class Meta:
                model = self.model
                fields = '__all__'
                exclude = ['created_at', 'updated_at']
            
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                user = request_obj.user
                if user.role == 'HOD':
                    try:
                        dept = user.faculty_profile.department
                        if dept:
                            for field_name, field in self.fields.items():
                                rel_model = getattr(field, 'queryset', None)
                                if rel_model is not None:
                                    m_name = rel_model.model.__name__
                                    if m_name == 'Subject':
                                        field.queryset = field.queryset.filter(branch__program__dept=dept)
                                    elif m_name == 'Student':
                                        field.queryset = field.queryset.filter(department=dept)
                                    elif m_name == 'FacultyProfile':
                                        field.queryset = field.queryset.filter(department=dept)
                                    elif m_name == 'Branch':
                                        field.queryset = field.queryset.filter(program__dept=dept)
                                    elif m_name == 'SubjectAllotment':
                                        field.queryset = field.queryset.filter(subject__branch__program__dept=dept)
                                    elif m_name == 'Project':
                                        field.queryset = field.queryset.filter(branch__program__dept=dept)
                    except Exception as e:
                        print(f"Form filter error: {e}")
                        pass
                elif user.role in ['TEACHER', 'FACULTY']:
                    try:
                        faculty = getattr(user, 'faculty_profile', None)
                        if faculty:
                            for field_name, field in self.fields.items():
                                rel_model = getattr(field, 'queryset', None)
                                if rel_model is not None:
                                    m_name = rel_model.model.__name__
                                    if m_name == 'Subject':
                                        field.queryset = field.queryset.filter(allotments__faculty=faculty)
                                    elif m_name == 'Student':
                                        field.queryset = field.queryset.filter(department=faculty.department)
                                    elif m_name == 'FacultyProfile':
                                        field.queryset = field.queryset.filter(id=faculty.id)
                                        self.initial[field_name] = faculty
                                    elif m_name == 'Branch':
                                        field.queryset = field.queryset.filter(program__dept=faculty.department)
                                    elif m_name == 'SubjectAllotment':
                                        field.queryset = field.queryset.filter(faculty=faculty)
                                    elif m_name == 'Project':
                                        field.queryset = field.queryset.filter(mentor=faculty)
                    except Exception as e:
                        print(f"Form filter error: {e}")
                        pass
                
                for field_name, field in self.fields.items():
                    field.widget.attrs.update({
                        'class': 'block w-full rounded-xl border border-gray-200 dark:border-gray-800 dark:bg-darkSurface dark:text-gray-100 p-3 shadow-sm focus:border-primary focus:ring-4 focus:ring-primary/5 sm:text-sm'
                    })
                    if isinstance(field.widget, forms.widgets.DateInput):
                        field.widget.input_type = 'date'
                    elif isinstance(field.widget, forms.widgets.TimeInput):
                        field.widget.input_type = 'time'
                    elif isinstance(field.widget, forms.widgets.DateTimeInput):
                        field.widget.input_type = 'datetime-local'
        return DynamicModelForm

TEACHER_ALLOWED_MODELS = [
    'assignment',
    'assignmentsubmission',
    'studentattendance',
    'subjectschedule',
    'project',
    'projectmember',
    'projectweeklylog',
    'projectdeliverable',
    'facultyleave',
    'facultyleavebalance',
    'facultydocument',
    'examschedule',
    'studymaterial',
]

TEACHER_READONLY_MODELS = ['subjectschedule', 'facultyleavebalance', 'examschedule']
TEACHER_NO_ADD_MODELS = ['assignmentsubmission']

STUDENT_ALLOWED_MODELS = [
]

class GenericModelPermissionMixin(RolePermissionMixin):
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        
        role = str(user.role).upper()
        if user.is_superuser or role in ['ADMIN', 'SUB_ADMIN']:
            return True
        if role == 'HOD':
            return True
        
        model_key = self.kwargs.get('model_name')
        if role in ['TEACHER', 'FACULTY']:
            return model_key in TEACHER_ALLOWED_MODELS
            
        if role == 'STUDENT':
            if model_key in STUDENT_ALLOWED_MODELS:
                view_name = self.__class__.__name__
                if view_name in ['GenericModelListView', 'GenericModelDetailView']:
                    return True
            return False
            
        return False

    def check_departmental_access(self, obj):
        user = self.request.user
        if user.is_superuser or str(user.role).upper() in ['ADMIN', 'SUB_ADMIN']:
            return
        
        role = str(user.role).upper()
        
        if role == 'HOD':
            try:
                dept = user.faculty_profile.department
                if not dept:
                    return
                
                obj_dept = None
                model_name = obj.__class__.__name__
                
                if hasattr(obj, 'department'):
                    obj_dept = obj.department
                elif hasattr(obj, 'faculty') and hasattr(obj.faculty, 'department'):
                    obj_dept = obj.faculty.department
                elif hasattr(obj, 'student') and hasattr(obj.student, 'department'):
                    obj_dept = obj.student.department
                elif hasattr(obj, 'subject') and hasattr(obj.subject, 'branch'):
                    obj_dept = getattr(obj.subject.branch.program, 'dept', None)
                elif hasattr(obj, 'branch') and hasattr(obj.branch, 'program'):
                    obj_dept = getattr(obj.branch.program, 'dept', None)
                elif model_name == 'SubjectSchedule':
                    obj_dept = getattr(obj.allotment.subject.branch.program, 'dept', None)
                elif model_name == 'ExamSchedule':
                    obj_dept = getattr(obj.subject.branch.program, 'dept', None)
                elif model_name == 'StudentAttendance':
                    obj_dept = obj.student.department
                elif model_name == 'Project':
                    obj_dept = getattr(obj.branch.program, 'dept', None)
                elif model_name in ['ProjectMember', 'ProjectWeeklyLog', 'ProjectDeliverable']:
                    obj_dept = getattr(obj.project.branch.program, 'dept', None)
                elif model_name == 'AssignmentSubmission':
                    obj_dept = obj.student.department
                elif model_name == 'Guardian':
                    obj_dept = obj.student.department
                elif model_name == 'CommunicationLog':
                    obj_dept = getattr(obj.sender.faculty_profile, 'department', None)

                if obj_dept and obj_dept != dept:
                    raise PermissionDenied("You do not have permission to access records outside your department.")
            except PermissionDenied as e:
                raise e
            except Exception:
                pass
                
        elif role in ['TEACHER', 'FACULTY']:
            try:
                faculty = getattr(user, 'faculty_profile', None)
                if not faculty:
                    raise PermissionDenied("Faculty profile not found.")
                
                model_name = obj.__class__.__name__
                allowed = False
                
                if model_name == 'Assignment':
                    allowed = (obj.faculty == faculty)
                elif model_name == 'AssignmentSubmission':
                    allowed = (obj.assignment.faculty == faculty)
                elif model_name == 'StudentAttendance':
                    allowed = (obj.allotment.faculty == faculty)
                elif model_name == 'SubjectSchedule':
                    allowed = (obj.allotment.faculty == faculty)
                elif model_name == 'Project':
                    allowed = (obj.mentor == faculty)
                elif model_name in ['ProjectMember', 'ProjectWeeklyLog', 'ProjectDeliverable']:
                    allowed = (obj.project.mentor == faculty)
                elif model_name in ['FacultyLeave', 'FacultyLeaveBalance', 'FacultyDocument']:
                    allowed = (obj.faculty == faculty)
                elif model_name == 'ExamSchedule':
                    allowed = obj.subject.allotments.filter(faculty=faculty).exists()
                elif model_name == 'StudyMaterial':
                    allowed = (obj.faculty == faculty)
                elif model_name == 'MidTermMark':
                    allowed = obj.subject.allotments.filter(faculty=faculty).exists()
                
                if not allowed:
                    raise PermissionDenied("You do not have permission to access this record.")
            except PermissionDenied as e:
                raise e
            except Exception as e:
                print(f"Teacher object permission check error: {e}")
                raise PermissionDenied("Error checking access permissions.")
                
        elif role == 'STUDENT':
            try:
                student = getattr(user, 'student_profile', None)
                if not student:
                    raise PermissionDenied("Student profile not found.")
                
                model_name = obj.__class__.__name__
                allowed = False
                
                if model_name == 'MidTermMark':
                    allowed = (obj.student == student)
                
                if not allowed:
                    raise PermissionDenied("You do not have permission to access this record.")
            except PermissionDenied as e:
                raise e
            except Exception as e:
                print(f"Student object permission check error: {e}")
                raise PermissionDenied("Error checking access permissions.")

class GenericModelListView(GenericModelPermissionMixin, GenericModelSetupMixin, ERPListView):
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        if user.is_superuser:
            return qs

        role = str(user.role).upper()
        if role == 'HOD' or user.has_role_permission('can_view_dept_data'):
            try:
                dept = user.faculty_profile.department
                if not dept:
                    return qs
                
                model_name = self.model.__name__
                
                if hasattr(self.model, 'department'):
                    qs = qs.filter(department=dept)
                elif hasattr(self.model, 'faculty') and hasattr(self.model.faculty.field.related_model, 'department'):
                    qs = qs.filter(faculty__department=dept)
                elif hasattr(self.model, 'student') and hasattr(self.model.student.field.related_model, 'department'):
                    qs = qs.filter(student__department=dept)
                elif hasattr(self.model, 'subject') and hasattr(self.model.subject.field.related_model, 'branch'):
                    qs = qs.filter(subject__branch__program__dept=dept)
                elif hasattr(self.model, 'branch') and hasattr(self.model.branch.field.related_model, 'program'):
                    qs = qs.filter(branch__program__dept=dept)
                elif model_name == 'SubjectSchedule':
                    qs = qs.filter(allotment__subject__branch__program__dept=dept)
                elif model_name == 'ExamSchedule':
                    qs = qs.filter(subject__branch__program__dept=dept)
                elif model_name == 'StudentAttendance':
                    qs = qs.filter(student__department=dept)
                elif model_name == 'Project':
                    qs = qs.filter(branch__program__dept=dept)
                elif model_name == 'ProjectMember':
                    qs = qs.filter(project__branch__program__dept=dept)
                elif model_name == 'ProjectWeeklyLog':
                    qs = qs.filter(project__branch__program__dept=dept)
                elif model_name == 'ProjectDeliverable':
                    qs = qs.filter(project__branch__program__dept=dept)
                elif model_name == 'AssignmentSubmission':
                    qs = qs.filter(student__department=dept)
                elif model_name == 'Guardian':
                    qs = qs.filter(student__department=dept)
                elif model_name == 'CommunicationLog':
                    qs = qs.filter(sender__faculty_profile__department=dept)
            except Exception as e:
                print(f"Generic HOD filtering error: {e}")
                pass
        elif role in ['TEACHER', 'FACULTY']:
            try:
                faculty = getattr(user, 'faculty_profile', None)
                if faculty:
                    model_name = self.model.__name__
                    if model_name == 'Assignment':
                        qs = qs.filter(faculty=faculty)
                    elif model_name == 'AssignmentSubmission':
                        qs = qs.filter(assignment__faculty=faculty)
                    elif model_name == 'StudentAttendance':
                        qs = qs.filter(allotment__faculty=faculty)
                    elif model_name == 'SubjectSchedule':
                        qs = qs.filter(allotment__faculty=faculty)
                    elif model_name == 'Project':
                        qs = qs.filter(mentor=faculty)
                    elif model_name == 'ProjectMember':
                        qs = qs.filter(project__mentor=faculty)
                    elif model_name == 'ProjectWeeklyLog':
                        qs = qs.filter(project__mentor=faculty)
                    elif model_name == 'ProjectDeliverable':
                        qs = qs.filter(project__mentor=faculty)
                    elif model_name in ['FacultyLeave', 'FacultyLeaveBalance', 'FacultyDocument']:
                        qs = qs.filter(faculty=faculty)
                    elif model_name == 'ExamSchedule':
                        qs = qs.filter(subject__allotments__faculty=faculty).distinct()
                    elif model_name == 'StudyMaterial':
                        qs = qs.filter(faculty=faculty)
                    elif model_name == 'MidTermMark':
                        qs = qs.filter(subject__allotments__faculty=faculty).distinct()
            except Exception as e:
                print(f"Generic Teacher filtering error: {e}")
                pass
        elif role == 'STUDENT':
            try:
                student = getattr(user, 'student_profile', None)
                if student:
                    model_name = self.model.__name__
                    if model_name == 'MidTermMark':
                        qs = qs.filter(student=student)
                    else:
                        qs = qs.none()
            except Exception as e:
                print(f"Generic Student filtering error: {e}")
                qs = qs.none()
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        role = str(user.role).upper()
        
        if role in ['TEACHER', 'FACULTY']:
            model_key = self.kwargs.get('model_name')
            context['can_add'] = model_key not in (TEACHER_READONLY_MODELS + TEACHER_NO_ADD_MODELS)
            context['can_edit'] = model_key not in TEACHER_READONLY_MODELS
        else:
            can_manage = user.is_superuser or role in ['ADMIN', 'SUB_ADMIN', 'HOD']
            context['can_add'] = can_manage
            context['can_edit'] = can_manage
            
        context['create_url'] = 'create/'
        return context

class GenericModelDetailView(GenericModelPermissionMixin, GenericModelSetupMixin, ERPDetailView):
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        self.check_departmental_access(obj)
        return obj

    def get_context_data(self, **kwargs):
        self.detail_fields = [f.name for f in self.model._meta.fields]
        return super().get_context_data(**kwargs)

class GenericModelCreateView(GenericModelPermissionMixin, GenericModelSetupMixin, ERPCreateView):
    pass

class GenericModelUpdateView(GenericModelPermissionMixin, GenericModelSetupMixin, ERPUpdateView):
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        self.check_departmental_access(obj)
        return obj

class GenericModelDeleteView(GenericModelPermissionMixin, GenericModelSetupMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            obj = self.model.objects.get(pk=self.kwargs['pk'])
            self.check_departmental_access(obj)
            obj.delete()
            messages.success(request, f"{self.module_name} deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting record: {str(e)}")
        return HttpResponseRedirect(self.get_success_url())

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


from django.http import HttpResponse
from apps.fees.models import FeeReceipt, FinancialExpense
import csv

def download_ledger_csv(request):
    if not request.user.is_authenticated or request.user.role not in ['ADMIN', 'SUB_ADMIN', 'ACCOUNTANT', 'HOD']:
        return HttpResponse("Unauthorized", status=403)
        
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="fee_collection_ledger.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Receipt No', 'Date', 'Student Name', 'Enrollment No', 'Semester', 'Branch', 'Amount', 'Payment Mode', 'Verified'])
    
    receipts = FeeReceipt.objects.select_related('student__user', 'student__branch').all().order_by('-transaction_date')
    for r in receipts:
        writer.writerow([
            r.receipt_no,
            r.transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
            r.student.user.get_full_name(),
            r.student.enrollment_number,
            r.student.semester,
            r.student.branch.branch_code if r.student.branch else '-',
            r.amount,
            r.get_payment_mode_display(),
            'Yes' if r.is_verified else 'No'
        ])
    return response

def daily_summary_report(request):
    if not request.user.is_authenticated or request.user.role not in ['ADMIN', 'SUB_ADMIN', 'ACCOUNTANT', 'HOD']:
        return HttpResponse("Unauthorized", status=403)
        
    from django.utils import timezone
    from django.db.models import Sum
    
    today = timezone.now().date()
    
    # Receipts today
    today_receipts = FeeReceipt.objects.filter(transaction_date__date=today).select_related('student__user')
    total_receipts_amount = today_receipts.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Expenses today
    today_expenses = FinancialExpense.objects.filter(expense_date=today)
    total_expenses_amount = today_expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="daily_financial_summary_{today.isoformat()}.csv"'
    
    writer = csv.writer(response)
    
    # Header Section
    writer.writerow(['DAILY FINANCIAL SUMMARY REPORT', today.strftime('%d %B, %Y')])
    writer.writerow([])
    
    # Overview
    writer.writerow(['Financial Overview'])
    writer.writerow(['Total Income (Revenue)', f'INR {total_receipts_amount:,.2f}'])
    writer.writerow(['Total Expenses', f'INR {total_expenses_amount:,.2f}'])
    writer.writerow(['Net Balance', f'INR {(total_receipts_amount - total_expenses_amount):,.2f}'])
    writer.writerow([])
    
    # Today's Collections Detail
    writer.writerow(["TODAY'S COLLECTIONS"])
    writer.writerow(['Receipt No', 'Student Name', 'Amount', 'Payment Mode'])
    for r in today_receipts:
        writer.writerow([r.receipt_no, r.student.user.get_full_name(), r.amount, r.get_payment_mode_display()])
    if not today_receipts.exists():
        writer.writerow(['No collections today', '', '', ''])
    writer.writerow([])
    
    # Today's Expenses Detail
    writer.writerow(["TODAY'S EXPENSES"])
    writer.writerow(['Expense Title', 'Category', 'Amount'])
    for e in today_expenses:
        writer.writerow([e.title, e.get_category_display(), e.amount])
    if not today_expenses.exists():
        writer.writerow(['No expenses today', '', ''])
        
    return response
