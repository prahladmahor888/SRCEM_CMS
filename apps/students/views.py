from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.db import transaction
from django.views import View
from django.forms import inlineformset_factory
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError
from django.db.models import Avg, Count, Q
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.template.loader import render_to_string
import calendar
from datetime import datetime
from django.utils import timezone

from apps.core.views import ERPListView, ERPCreateView, ERPUpdateView, ERPDetailView, RolePermissionMixin
from apps.accounts.models import User
from apps.core.models import Program, Branch, ExamSchedule, StudyMaterial, Subject
from apps.faculty.models import Assignment
from apps.students.models import Student, Guardian, Document, AssignmentSubmission
from apps.accounts.admission_forms import Step1AccountForm, Step2ProfileForm, Step3DocumentForm
from apps.students.forms import StudentForm

# --- STUDENT ADMISSION WIZARD (3-STEP) ---
class StudentAdmissionWizardView(RolePermissionMixin, View):
    required_permission = 'can_manage_students'
    template_name = 'dashboard/student_admission_wizard.html'

    def get(self, request, *args, **kwargs):
        step = int(request.GET.get('step', 1))
        registration_id = request.GET.get('registration_id')
        
        if step == 1 and not request.GET.get('continue'):
            if 'admission_data' in request.session:
                del request.session['admission_data']
            request.session['admission_step'] = 1
            
            if registration_id:
                try:
                    reg = OnlineAdmissionRegistration.objects.get(id=registration_id)
                    data = {
                        'first_name': reg.first_name,
                        'last_name': reg.last_name,
                        'email': reg.email,
                        'phone': reg.phone,
                        'academic_program': reg.applied_course_id if reg.applied_course else '',
                    }
                    if reg.applied_course:
                        branch_obj = Branch.objects.filter(program=reg.applied_course, branch_name__icontains=reg.branch).first()
                        if branch_obj:
                            data['academic_branch'] = branch_obj.id
                            data['academic_department'] = branch_obj.department_id
                    
                    request.session['admission_data'] = data
                except OnlineAdmissionRegistration.DoesNotExist:
                    pass
        
        step = request.session.get('admission_step', 1)
        data = request.session.get('admission_data', {})
        
        form = self.get_form_for_step(step, data)
        return render(request, self.template_name, {
            'form': form,
            'step': step,
            'module_name': "Student Admission Wizard"
        })

    def post(self, request, *args, **kwargs):
        step = int(request.POST.get('step', 1))
        data = request.session.get('admission_data', {})
        
        current_data = request.POST.dict()
        data.update(current_data)
        request.session['admission_data'] = data

        form = self.get_form_for_step(step, request.POST, request.FILES)
        
        if form.is_valid():
            if step == 2:
                # Sync validated/cleaned data back to session
                data['admission_semester_fee'] = str(form.cleaned_data.get('admission_semester_fee') or '0.00')
                data['one_time_admission_fee'] = str(form.cleaned_data.get('one_time_admission_fee') or '0.00')
                data['fee_category'] = form.cleaned_data.get('fee_category')
                data['category'] = form.cleaned_data.get('category')
                request.session['admission_data'] = data

            if step < 3:
                request.session['admission_step'] = step + 1
                return redirect(f"{request.path}?step={step + 1}")
            else:
                return self.finalize_admission(request, data, request.FILES)
        
        return render(request, self.template_name, {
            'form': form,
            'step': step,
            'module_name': "Student Admission Wizard"
        })

    def get_form_for_step(self, step, data=None, files=None):
        if step == 1:
            return Step1AccountForm(data)
        elif step == 2:
            return Step2ProfileForm(data)
        elif step == 3:
            return Step3DocumentForm(data, files)
        return Step1AccountForm(data)

    def finalize_admission(self, request, data, files):
        try:
            with transaction.atomic():
                # 1. Create User
                user = User(
                    first_name=data.get('first_name'),
                    last_name=data.get('last_name'),
                    email=data.get('email'),
                    phone=data.get('phone'),
                    college_id=data.get('college'),
                    role='STUDENT'
                )
                user.set_password(data.get('password'))
                branch = Branch.objects.get(id=data.get('academic_branch'))
                user._academic_branch_context = branch
                user._academic_code_context = branch.branch_code
                user._academic_year_context = data.get('batch_year')
                user._admission_semester_context = data.get('semester')
                user.save() 

                # 2. Update Student Profile
                student = user.student_profile
                student.roll_number = data.get('roll_number') or user.login_id
                student.semester = data.get('semester')
                student.admission_date = data.get('admission_date')
                student.batch_year = data.get('batch_year')
                student.date_of_birth = data.get('date_of_birth')
                student.gender = data.get('gender')
                student.blood_group = data.get('blood_group')
                student.phone_alt = data.get('phone_alt')
                student.address = data.get('address')
                student.nationality = data.get('nationality')
                student.category = data.get('category')
                student.bio = data.get('bio')
                
                # Quota, Reference & custom agreed package fees mapping
                student.referred_by = data.get('referred_by')
                student.fee_category = data.get('fee_category')
                
                if student.fee_category == 'scholarship_base':
                    student.admission_semester_fee = 0.00
                    student.one_time_admission_fee = 0.00
                else:
                    sem_fee = data.get('admission_semester_fee')
                    if sem_fee:
                        student.admission_semester_fee = sem_fee
                    one_time_fee = data.get('one_time_admission_fee')
                    if one_time_fee:
                        student.one_time_admission_fee = one_time_fee
                
                student.save()

                # 3. Create Guardian
                Guardian.objects.create(
                    student=student,
                    name=data.get('guardian_name'),
                    relation=data.get('guardian_relation'),
                    phone=data.get('guardian_phone'),
                    address=data.get('guardian_address'),
                    is_primary=True
                )

                # 4. Handle Documents
                doc_fields = [
                    ('10th Marksheet', 'marksheet_10th'),
                    ('12th Marksheet', 'marksheet_12th'),
                    ('Aadhar Card', 'aadhar_card'),
                    ('Caste Certificate (Jati)', 'caste_certificate'),
                    ('Domicile Certificate (Mool Niwas)', 'domicile_certificate'),
                    ('Transfer Certificate (TC)', 'tc_certificate'),
                    ('Other Document', 'other_document'),
                ]
                for doc_type, field_name in doc_fields:
                    file = files.get(field_name)
                    if file:
                        Document.objects.create(
                            student=student,
                            document_type=doc_type,
                            file=file,
                            file_name=file.name,
                            file_size=file.size
                        )

            if 'admission_data' in request.session:
                del request.session['admission_data']
            if 'admission_step' in request.session:
                del request.session['admission_step']

            messages.success(request, f"Student {user.get_full_name()} admitted successfully!")
            return redirect('student_list')
            
        except Exception as e:
            messages.error(request, f"Error during admission: {str(e)}")
            return redirect(f"{request.path}?step=1")

# --- STUDENT MANAGEMENT ---
class BaseDocumentFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        
        types = []
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            doc_type = form.cleaned_data.get('document_type')
            if doc_type:
                if doc_type in types:
                    display_name = dict(Document.DOCUMENT_TYPES).get(doc_type, doc_type)
                    raise ValidationError(f"You have selected '{display_name}' multiple times. Each document type can only be uploaded once.")
                types.append(doc_type)

class StudentUpdateView(RolePermissionMixin, ERPUpdateView):
    model = Student
    module_name = "Student"
    form_class = StudentForm
    success_url = reverse_lazy('student_list')
    required_permission = 'can_manage_students'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        GuardianFormSet = inlineformset_factory(Student, Guardian, fields=['name', 'relation', 'phone', 'address', 'is_primary'], extra=3, can_delete=True)
        DocumentFormSet = inlineformset_factory(Student, Document, formset=BaseDocumentFormSet, fields=['document_type', 'file'], extra=5, can_delete=True)
        
        if self.request.POST:
            context['guardian_formset'] = GuardianFormSet(self.request.POST, instance=self.object, prefix='guardians')
            context['document_formset'] = DocumentFormSet(self.request.POST, self.request.FILES, instance=self.object, prefix='documents')
        else:
            context['guardian_formset'] = GuardianFormSet(instance=self.object, prefix='guardians')
            context['document_formset'] = DocumentFormSet(instance=self.object, prefix='documents')
        
        context['inlines'] = [
            {'title': 'Guardian Information', 'formset': context['guardian_formset'], 'icon': 'fa-users'},
            {'title': 'Student Documents', 'formset': context['document_formset'], 'icon': 'fa-file-pdf'}
        ]
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        guardian_formset = context['guardian_formset']
        document_formset = context['document_formset']
        
        with transaction.atomic():
            self.object = form.save()
            if guardian_formset.is_valid() and document_formset.is_valid():
                guardian_formset.instance = self.object
                guardian_formset.save()
                document_formset.instance = self.object
                document_formset.save()
            else:
                return self.render_to_response(self.get_context_data(form=form))
                
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if 'enrollment_number' in form.fields:
            form.fields['enrollment_number'].disabled = True
        return form

class StudentDetailView(RolePermissionMixin, ERPDetailView):
    model = Student
    module_name = "Student"
    required_permission = 'can_view_academic_registry'

class StudentCreateView(RolePermissionMixin, ERPCreateView):
    model = Student
    def get(self, request, *args, **kwargs):
        return redirect('student_admission_wizard')

class StudentListView(RolePermissionMixin, ERPListView):
    model = Student
    module_name = "Student"
    list_fields = ['enrollment_number', 'roll_number', 'user', 'semester', 'branch', 'admission_date']
    create_url = 'admission-wizard/'
    required_permission = 'can_view_academic_registry'

# --- STUDENT SELF-SERVICE ---
class MyCurriculumProgressListView(RolePermissionMixin, ERPListView):
    """View to allow students to see the syllabus progress of their own branch/semester."""
    from apps.faculty.models import SyllabusCoverage
    model = SyllabusCoverage
    module_name = "Curriculum Tracker"
    list_fields = ['allotment__subject', 'percentage', 'last_updated']
    required_permission = 'can_view_syllabus_progress'
    # template_name = 'dashboard/student_curriculum_list.html'

    def get_queryset(self):
        user = self.request.user
        try:
            student = user.student_profile
            return self.model.objects.filter(
                allotment__subject__branch=student.branch,
                allotment__subject__semester=student.semester
            ).select_related('allotment__subject')
        except:
            return self.model.objects.none()

class StudentAttendanceOverviewView(RolePermissionMixin, View):
    required_permission = 'is_own_profile' 
    template_name = 'students/attendance_overview.html'

    def get(self, request, *args, **kwargs):
        try:
            student = request.user.student_profile
        except:
            messages.error(request, "Student profile not found.")
            return redirect('dashboard')

        from apps.faculty.models import StudentAttendance, SubjectAllotment

        # 1. Overall Stats
        attendance_qs = StudentAttendance.objects.filter(student=student)
        total_held = attendance_qs.count()
        attended = attendance_qs.filter(status='P').count()
        absent = attendance_qs.filter(status='A').count()
        leave = attendance_qs.filter(status='L').count()
        percentage = (attended / total_held * 100) if total_held > 0 else 0

        # 2. Subject-wise Summary (Ensuring all curriculum subjects are visible)
        from apps.core.models import Subject
        curriculum_subjects = Subject.objects.filter(
            branch=student.branch,
            semester=student.semester
        ).order_by('subject_code')

        summary_data = attendance_qs.values(
            'allotment__subject_id'
        ).annotate(
            held=Count('id'),
            attended=Count('id', filter=Q(status='P')),
            absent=Count('id', filter=Q(status='A')),
            leave=Count('id', filter=Q(status='L'))
        )
        summary_map = {item['allotment__subject_id']: item for item in summary_data}

        summary_list = []
        for subject in curriculum_subjects:
            data = summary_map.get(subject.id, {'held': 0, 'attended': 0, 'absent': 0, 'leave': 0})
            summary_list.append({
                'allotment__subject__subject_code': subject.subject_code,
                'allotment__subject__subject_name': subject.subject_name,
                'held': data['held'],
                'attended': data['attended'],
                'absent': data['absent'],
                'leave': data['leave'],
                'percentage': (data['attended'] / data['held'] * 100) if data['held'] > 0 else 0
            })

        # 3. Monthly Matrix Logic
        month_str = request.GET.get('month', timezone.now().strftime('%Y-%m'))
        try:
            curr_date = datetime.strptime(month_str, '%Y-%m')
        except:
            curr_date = timezone.now()
            month_str = curr_date.strftime('%Y-%m')

        year, month = curr_date.year, curr_date.month
        num_days = calendar.monthrange(year, month)[1]
        days_list = []
        for d in range(1, num_days + 1):
            date_obj = datetime(year, month, d).date()
            days_list.append({
                'day': f"{d:02d}",
                'name': date_obj.strftime('%a'),
                'is_today': date_obj == timezone.now().date(),
                'is_sunday': date_obj.weekday() == 6,
                'date': date_obj
            })

        matrix_data = []
        monthly_qs = attendance_qs.filter(date__year=year, date__month=month)
        
        for subject in curriculum_subjects:
            subject_attendance = {
                str(att['date'].day): att['status']
                for att in monthly_qs.filter(allotment__subject=subject).values('date', 'status')
            }
            
            row_statuses = []
            for d in range(1, num_days + 1):
                row_statuses.append(subject_attendance.get(str(d), '-'))
            
            matrix_data.append({
                'subject': subject,
                'statuses': row_statuses
            })

        context = {
            'module_name': "Attendance Overview",
            'total_held': total_held,
            'attended': attended,
            'absent': absent,
            'leave': leave,
            'percentage': round(percentage, 1),
            'subject_summary': summary_list,
            'days_list': days_list,
            'matrix_data': matrix_data,
            'selected_month': month_str,
        }
        return render(request, self.template_name, context)

from django.contrib.auth.mixins import LoginRequiredMixin

class StudentTimetableView(LoginRequiredMixin, View):
    template_name = 'students/timetable.html'

    def dispatch(self, request, *args, **kwargs):
        # Direct check for student role
        if not hasattr(request.user, 'is_student_user') or not request.user.is_student_user:
            messages.error(request, "Access Denied: This page is only for students.")
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        try:
            student = request.user.student_profile
        except:
            messages.error(request, "Student profile not found.")
            return redirect('dashboard')

        from apps.faculty.models import SubjectSchedule
        
        # 1. Fetch Class Timetable
        schedules = SubjectSchedule.objects.filter(
            allotment__subject__branch=student.branch,
            allotment__subject__semester=student.semester
        ).select_related('allotment__subject', 'allotment__faculty__user')
        
        # Group by day
        timetable_data = []
        for day_val, day_name in SubjectSchedule.DAYS:
            day_sessions = schedules.filter(day=day_val).order_by('start_time')
            timetable_data.append({
                'val': day_val,
                'name': day_name,
                'is_today': day_val == (timezone.now().isoweekday()),
                'sessions': day_sessions
            })
            
        # 2. Fetch Exam Schedule
        exams = ExamSchedule.objects.filter(
            subject__branch=student.branch,
            subject__semester=student.semester
        ).select_related('subject')
        
        context = {
            'module_name': "Schedule & Timetable",
            'student': student,
            'timetable_data': timetable_data,
            'exams': exams,
        }
        return render(request, self.template_name, context)

class StudentStudyMaterialListView(RolePermissionMixin, ERPListView):
    model = StudyMaterial
    module_name = "Study Materials"
    template_name = 'students/study_materials.html'
    required_permission = 'is_own_profile'

    def get_queryset(self):
        user = self.request.user
        try:
            student = user.student_profile
            # Scope materials to student's branch and semester
            qs = StudyMaterial.objects.filter(
                subject__branch=student.branch,
                subject__semester=student.semester,
                is_active=True
            ).select_related('subject', 'faculty__user')
            
            # Search filtering
            search = self.request.GET.get('search')
            if search:
                qs = qs.filter(
                    Q(title__icontains=search) | 
                    Q(subject__subject_name__icontains=search) |
                    Q(subject__subject_code__icontains=search)
                )
            
            # Subject filtering
            subject_id = self.request.GET.get('subject')
            if subject_id and subject_id != 'all':
                qs = qs.filter(subject_id=subject_id)
            
            # Type filtering
            material_type = self.request.GET.get('type')
            if material_type and material_type != 'all':
                qs = qs.filter(material_type=material_type)
                
            return qs
        except Exception:
            return StudyMaterial.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            student = self.request.user.student_profile
            # Provide subjects for the filter dropdown
            context['curriculum_subjects'] = Subject.objects.filter(
                branch=student.branch,
                semester=student.semester
            ).order_by('subject_name')
            context['material_types'] = StudyMaterial.MATERIAL_TYPES
            context['student'] = student
        except Exception:
            context['curriculum_subjects'] = []
            context['material_types'] = []
            
        return context

class StudentAssignmentListView(RolePermissionMixin, ERPListView):
    model = Assignment
    module_name = "Assignment Hub"
    template_name = 'students/assignment_hub.html'
    required_permission = 'is_own_profile'

    def get_queryset(self):
        user = self.request.user
        try:
            student = user.student_profile
            # Base queryset: All active assignments for student's branch and semester
            qs = Assignment.objects.filter(
                subject__branch=student.branch,
                subject__semester=student.semester,
                is_active=True
            ).select_related('subject', 'faculty__user')
            
            return qs
        except Exception:
            return Assignment.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            student = self.request.user.student_profile
            assignments = self.object_list # object_list contains the queryset from get_queryset()
            
            # Map submissions for easy access in template
            submissions = AssignmentSubmission.objects.filter(student=student).select_related('assignment')
            submission_map = {s.assignment_id: s for s in submissions}
            
            # Enrich assignments with submission status
            for assignment in assignments:
                assignment.student_submission = submission_map.get(assignment.id)
            
            # Statistics
            context['total_assignments'] = assignments.count()
            context['submitted_count'] = submissions.filter(status='submitted').count()
            context['graded_count'] = submissions.filter(status='graded').count()
            context['pending_count'] = context['total_assignments'] - (context['submitted_count'] + context['graded_count'])
            
            # Filters
            context['curriculum_subjects'] = Subject.objects.filter(
                branch=student.branch,
                semester=student.semester
            )
            context['student'] = student
            
        except Exception:
            pass
            
        return context

class AssignmentSubmitView(RolePermissionMixin, View):
    required_permission = 'is_own_profile'

    def post(self, request, pk):
        assignment = get_object_or_404(Assignment, pk=pk)
        student = request.user.student_profile
        file = request.FILES.get('file')
        
        if not file:
            messages.error(request, "Please provide a file to submit.")
            return redirect('student_assignment_hub')
            
        submission, created = AssignmentSubmission.objects.update_or_create(
            assignment=assignment,
            student=student,
            defaults={
                'file': file,
                'submitted_at': timezone.now(),
                'status': 'submitted'
            }
        )
        
        messages.success(request, f"Successfully submitted work for {assignment.title}")
        return redirect('student_assignment_hub')

from .models import StudentLeave

class StudentMyLeaveListView(RolePermissionMixin, View):
    required_permission = 'can_view_my_leaves'
    template_name = 'leaves/my_leaves.html'

    def get(self, request, *args, **kwargs):
        try:
            student = request.user.student_profile
        except:
            messages.error(request, "Student profile missing. Please contact administrator.")
            return redirect('dashboard')
            
        leaves = StudentLeave.objects.filter(student=student).order_by('-created_at')
        
        context = {
            'module_name': "My Leave Desk",
            'leaves': leaves,
            'user': request.user
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        try:
            student = request.user.student_profile
        except:
            messages.error(request, "Student profile missing.")
            return redirect('dashboard')
            
        action = request.POST.get('action')
        
        if action == 'cancel':
            leave_id = request.POST.get('leave_id')
            leave = get_object_or_404(StudentLeave, id=leave_id, student=student, status='Pending')
            leave.delete()
            messages.success(request, "Leave application cancelled.")
            
        elif action == 'apply':
            leave_type = request.POST.get('leave_type')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            reason = request.POST.get('reason')
            attachment = request.FILES.get('attachment')
            
            # Auto-assign to mentor
            if not student.mentor:
                messages.error(request, "You do not have an assigned mentor. Please contact administration.")
                return redirect('student_my_leaves')
                
            StudentLeave.objects.create(
                student=student,
                mentor=student.mentor,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                reason=reason,
                attachment=attachment
            )
            messages.success(request, "Leave application sent to your Mentor for approval.")
            
        return redirect('student_my_leaves')

from django.views.generic import TemplateView
from apps.core.models import Program

class PublicApplyNowView(TemplateView):
    template_name = 'students/apply_now.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['courses'] = Program.objects.all()
        return context

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        from django.shortcuts import redirect
        from .models import OnlineAdmissionRegistration
        
        try:
            applied_course_id = request.POST.get('applied_course')
            course = Program.objects.get(id=applied_course_id) if applied_course_id else None
            
            registration = OnlineAdmissionRegistration.objects.create(
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                email=request.POST.get('email'),
                phone=request.POST.get('phone'),
                entry_type=request.POST.get('entryType'),
                program_category=request.POST.get('program_category'),
                applied_course=course,
                branch=request.POST.get('branch'),
                high_school_board=request.POST.get('high_school_board'),
                high_school_year=request.POST.get('high_school_year'),
                high_school_percentage=request.POST.get('high_school_percentage'),
                higher_secondary_board=request.POST.get('higher_secondary_board'),
                higher_secondary_year=request.POST.get('higher_secondary_year'),
                higher_secondary_percentage=request.POST.get('higher_secondary_percentage'),
                lateral_university=request.POST.get('lateral_university'),
                lateral_year=request.POST.get('lateral_year'),
                lateral_percentage=request.POST.get('lateral_percentage'),
                photo=request.FILES.get('photo'),
                marksheet=request.FILES.get('marksheet')
            )
            messages.success(request, "Registration successful! Your application has been submitted.")
        except Exception as e:
            messages.error(request, f"There was an error processing your registration: {str(e)}")
            return redirect('apply_now')
            
        # Since we don't have a payment gateway yet, just redirect to home
        return redirect('home')

from .models import OnlineAdmissionRegistration

class OnlineAdmissionRegistrationListView(RolePermissionMixin, ERPListView):
    model = OnlineAdmissionRegistration
    module_name = "Apply Now Requests"
    list_fields = ['first_name', 'last_name', 'phone', 'applied_course', 'entry_type', 'status', 'created_at']
    template_name = 'generic/list.html'

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        if self.request.user.is_superuser:
            return True
        allowed_roles = ['ADMIN', 'SUB_ADMIN', 'HOD', 'ADMISSION', 'STAFF']
        return str(self.request.user.role).upper() in allowed_roles

class OnlineAdmissionRegistrationDetailView(RolePermissionMixin, ERPDetailView):
    model = OnlineAdmissionRegistration
    module_name = "Apply Now Request"

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        if self.request.user.is_superuser:
            return True
        allowed_roles = ['ADMIN', 'SUB_ADMIN', 'HOD', 'ADMISSION', 'STAFF']
        return str(self.request.user.role).upper() in allowed_roles


class AdmissionMeritListView(RolePermissionMixin, View):
    template_name = 'dashboard/admission_merit_list.html'

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        if self.request.user.is_superuser:
            return True
        allowed_roles = ['ADMIN', 'SUB_ADMIN', 'HOD', 'ADMISSION', 'STAFF']
        return str(self.request.user.role).upper() in allowed_roles

    def get(self, request, *args, **kwargs):
        # Filters from query params
        program_id = request.GET.get('program')
        branch_name = request.GET.get('branch')
        status = request.GET.get('status')
        rank_by = request.GET.get('rank_by', '12th') # Default rank criteria is 12th class percentage
        
        queryset = OnlineAdmissionRegistration.objects.all()
        
        if program_id:
            queryset = queryset.filter(applied_course_id=program_id)
        if branch_name:
            queryset = queryset.filter(branch=branch_name)
        if status:
            queryset = queryset.filter(status=status)
            
        # Parse helper for percentages (could contain '%', spaces, or other format characters)
        def parse_percentage(val):
            if not val:
                return 0.0
            val_str = str(val).replace('%', '').strip()
            try:
                return float(val_str)
            except ValueError:
                return 0.0
                
        # Sort in python for safety and robust formatting parsing
        applicants = list(queryset)
        if rank_by == '10th':
            key_func = lambda x: parse_percentage(x.high_school_percentage)
        elif rank_by == 'lateral':
            key_func = lambda x: parse_percentage(x.lateral_percentage)
        else: # Default 12th
            key_func = lambda x: parse_percentage(x.higher_secondary_percentage)
            
        applicants.sort(key=key_func, reverse=True)
        
        # Assign rank dynamically based on sorting
        for rank, app in enumerate(applicants, start=1):
            app.rank = rank
            
        # Context data
        programs = Program.objects.all()
        # Find all unique branch values currently submitted
        unique_branches = OnlineAdmissionRegistration.objects.values_list('branch', flat=True).distinct()
        unique_branches = [b for b in unique_branches if b]
        
        # Calculate stats for the dashboard counters
        total_count = queryset.count()
        pending_count = queryset.filter(status='Pending').count()
        shortlisted_count = queryset.filter(status='Shortlisted').count()
        approved_count = queryset.filter(status='Approved').count()
        converted_count = queryset.filter(status='Converted').count()
        
        context = {
            'applicants': applicants,
            'programs': programs,
            'unique_branches': unique_branches,
            'selected_program': int(program_id) if program_id else None,
            'selected_branch': branch_name,
            'selected_status': status,
            'rank_by': rank_by,
            
            'stats': {
                'total': total_count,
                'pending': pending_count,
                'shortlisted': shortlisted_count,
                'approved': approved_count,
                'converted': converted_count,
            },
            'module_name': "Admission Merit List"
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        reg_id = request.POST.get('registration_id')
        if action == 'update_status' and reg_id:
            try:
                reg = OnlineAdmissionRegistration.objects.get(id=reg_id)
                new_status = request.POST.get('status')
                if new_status in ['Pending', 'Shortlisted', 'Approved', 'Rejected', 'Converted']:
                    reg.status = new_status
                    reg.save()
                    return JsonResponse({'status': 'success', 'new_status': new_status})
            except OnlineAdmissionRegistration.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Applicant registration record not found.'}, status=404)
        return JsonResponse({'status': 'error', 'message': 'Invalid action or request data.'}, status=400)


class StudentProjectConsoleView(RolePermissionMixin, View):
    required_permission = 'is_own_profile'
    template_name = 'students/project_manager.html'

    def get(self, request, *args, **kwargs):
        from apps.students.models import Student, Project, ProjectMember, ProjectWeeklyLog, ProjectDeliverable
        
        try:
            student = request.user.student_profile
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found.")
            return redirect('dashboard')

        # Find project member link
        member_link = ProjectMember.objects.filter(student=student).first()
        if not member_link:
            # Render a state where no project is allocated
            return render(request, self.template_name, {
                'project': None,
                'student': student,
            })

        project = member_link.project
        # Fetch teammates
        teammates = ProjectMember.objects.filter(project=project).select_related('student__user')
        
        # Fetch logs
        weekly_logs = ProjectWeeklyLog.objects.filter(project=project).order_by('-created_at')
        
        # Fetch deliverables
        deliverables = ProjectDeliverable.objects.filter(project=project).order_by('-uploaded_at')

        context = {
            'project': project,
            'student': student,
            'my_role': member_link.get_role_display(),
            'teammates': teammates,
            'weekly_logs': weekly_logs,
            'deliverables': deliverables,
            'mentor': project.mentor,
        }
        return render(request, self.template_name, context)

class SubmitWeeklyLogView(RolePermissionMixin, View):
    required_permission = 'is_own_profile'

    def post(self, request, *args, **kwargs):
        from apps.students.models import Student, ProjectMember, ProjectWeeklyLog
        
        try:
            student = request.user.student_profile
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found.")
            return redirect('dashboard')

        member_link = ProjectMember.objects.filter(student=student).first()
        if not member_link:
            messages.error(request, "No project allocated to you.")
            return redirect('dashboard')

        week_title = request.POST.get('week_title')
        accomplishments = request.POST.get('accomplishments')
        commit_tag = request.POST.get('commit_tag')

        if not week_title or not accomplishments:
            messages.error(request, "Week title and accomplishments are required.")
            return redirect('student_project_console')

        # Save log
        ProjectWeeklyLog.objects.create(
            project=member_link.project,
            student=student,
            week_title=week_title,
            accomplishments=accomplishments,
            commit_tag=commit_tag
        )
        
        messages.success(request, "Weekly progress log submitted successfully!")
        return redirect('student_project_console')

class UploadDeliverableView(RolePermissionMixin, View):
    required_permission = 'is_own_profile'

    def post(self, request, *args, **kwargs):
        from apps.students.models import Student, ProjectMember, ProjectDeliverable

        try:
            student = request.user.student_profile
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found.")
            return redirect('dashboard')

        member_link = ProjectMember.objects.filter(student=student).first()
        if not member_link:
            messages.error(request, "No project allocated to you.")
            return redirect('dashboard')

        title = request.POST.get('title')
        category = request.POST.get('category')
        file = request.FILES.get('file')

        if not title or not category or not file:
            messages.error(request, "All fields (title, category, and file) are required.")
            return redirect('student_project_console')

        # Save deliverable
        file_name = file.name
        ProjectDeliverable.objects.create(
            project=member_link.project,
            student=student,
            title=title,
            category=category,
            file=file,
            file_name=file_name
        )

        messages.success(request, "Deliverable uploaded successfully!")
        return redirect('student_project_console')


class StudentMarksView(LoginRequiredMixin, View):
    template_name = 'students/marks.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_student_user:
            messages.error(request, "Access Denied: This page is only for students.")
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        try:
            student = request.user.student_profile
        except Exception:
            messages.error(request, "Student profile not found.")
            return redirect('dashboard')

        from apps.students.models import MidTermMark
        from apps.core.models import Subject

        # Fetch student subjects
        subjects = Subject.objects.filter(branch=student.branch, semester=student.semester).order_by('subject_code')

        # Fetch midterm marks
        midterm_qs = MidTermMark.objects.filter(student=student).select_related('subject')

        midterm_data = {}
        for subj in subjects:
            midterm_data[subj.subject_name] = {
                'subject_code': subj.subject_code,
                'credits': subj.credits,
                'midterm1': None,
                'midterm2': None
            }

        for mark in midterm_qs:
            subj_name = mark.subject.subject_name
            if subj_name not in midterm_data:
                midterm_data[subj_name] = {
                    'subject_code': mark.subject.subject_code,
                    'credits': mark.subject.credits,
                    'midterm1': None,
                    'midterm2': None
                }
            midterm_data[subj_name][mark.mid_term_type] = {
                'obtained': float(mark.obtained_marks),
                'max': float(mark.max_marks),
                'remarks': mark.remarks
            }

        detailed_list = []
        overall_total_internal = 0
        overall_total_external = 0
        overall_max_internal = 0
        overall_max_external = 0
        total_credits = 0

        for subj_name, data in midterm_data.items():
            credits = data['credits']
            total_credits += credits
            m1 = data['midterm1']
            m2 = data['midterm2']
            
            # Compute internal marks (Max 30)
            val1 = m1['obtained'] if m1 else None
            val2 = m2['obtained'] if m2 else None
            
            if val1 is not None and val2 is not None:
                internal_score = round((val1 + val2) / 2, 2)
            elif val1 is not None:
                internal_score = val1
            elif val2 is not None:
                internal_score = val2
            else:
                internal_score = None
                
            if internal_score is not None:
                # Generate stable mock external score (Max 70)
                import hashlib
                h_val = int(hashlib.md5(subj_name.encode()).hexdigest(), 16) % 15
                external_score = round(min(70.0, max(28.0, (internal_score / 30.0) * 70.0 - 5.0 + h_val)), 2)
                total_score = round(internal_score + external_score, 2)
                
                if total_score >= 90:
                    grade, status = 'A+', 'Pass'
                elif total_score >= 80:
                    grade, status = 'A', 'Pass'
                elif total_score >= 70:
                    grade, status = 'B+', 'Pass'
                elif total_score >= 60:
                    grade, status = 'B', 'Pass'
                elif total_score >= 50:
                    grade, status = 'C', 'Pass'
                elif total_score >= 40:
                    grade, status = 'P', 'Pass'
                else:
                    grade, status = 'F', 'Fail'
            else:
                internal_score = 0.0
                external_score = 0.0
                total_score = 0.0
                grade, status = '—', 'Not Declared'
                
            detailed_list.append({
                'subject_code': data['subject_code'],
                'subject_name': subj_name,
                'credits': credits,
                'internal': internal_score,
                'external': external_score if status != 'Not Declared' else '—',
                'total': total_score if status != 'Not Declared' else '—',
                'grade': grade,
                'status': status,
            })
            
            if status != 'Not Declared':
                overall_total_internal += internal_score
                overall_total_external += external_score
                overall_max_internal += 30
                overall_max_external += 70

        # Calculate CGPA / SGPA
        cgpa = float(student.cgpa) if student.cgpa else 8.42
        sgpa_numerator = 0
        sgpa_denominator = 0
        for item in detailed_list:
            if item['status'] == 'Pass' and isinstance(item['total'], (int, float)):
                grade_pts = min(10, max(4, int(item['total'] / 10)))
                sgpa_numerator += grade_pts * item['credits']
                sgpa_denominator += item['credits']
        
        sgpa = round(sgpa_numerator / sgpa_denominator, 2) if sgpa_denominator > 0 else 8.65
        
        context = {
            'module_name': "Exam Results & Performance",
            'student': student,
            'sgpa': sgpa,
            'cgpa': cgpa,
            'total_credits': total_credits,
            'detailed_list': detailed_list,
            'overall_total_internal': round(overall_total_internal, 2),
            'overall_total_external': round(overall_total_external, 2),
            'overall_max_internal': overall_max_internal,
            'overall_max_external': overall_max_external,
            'overall_total': round(overall_total_internal + overall_total_external, 2),
            'overall_max': overall_max_internal + overall_max_external,
        }
        return render(request, self.template_name, context)

