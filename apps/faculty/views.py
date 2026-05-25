from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.db import transaction
from django.views import View
from django.forms import inlineformset_factory
from django.db.models import Avg, Count
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.template.loader import render_to_string

from apps.core.views import ERPListView, ERPCreateView, ERPUpdateView, ERPDetailView, RolePermissionMixin
from apps.accounts.models import User
from apps.core.models import Department, Branch, Subject, SubjectTopic
from apps.faculty.models import (
    FacultyProfile, SubjectAllotment, SubjectSchedule, 
    SyllabusCoverage, FacultyDocument, ResearchPublication,
    StudentAttendance
)
from apps.students.models import Student, StudentLeave
from apps.faculty.forms import (
    FacultyStep1AccountForm, FacultyStep2ProfessionalForm, FacultyStep3DocumentForm, 
    SubjectAllotmentForm, SubjectScheduleForm, SubjectScheduleCreateForm, SyllabusTopicForm
)

# --- FACULTY ADMISSION WIZARD ---
class FacultyAdmissionWizardView(RolePermissionMixin, View):
    required_permission = 'can_manage_faculty'
    template_name = 'dashboard/faculty_admission_wizard.html'

    def get(self, request, *args, **kwargs):
        step = int(request.GET.get('step', 1))
        
        if request.GET.get('discard'):
            if 'faculty_admission_data' in request.session:
                del request.session['faculty_admission_data']
            request.session['faculty_admission_step'] = 1
            return redirect(f"{request.path}?step=1")

        if step == 1 and not request.GET.get('continue'):
            if 'faculty_admission_data' in request.session:
                del request.session['faculty_admission_data']
            request.session['faculty_admission_step'] = 1
        
        step = request.session.get('faculty_admission_step', 1)
        data = request.session.get('faculty_admission_data', {})
        
        form = self.get_form_for_step(step, data)
        return render(request, self.template_name, {
            'form': form,
            'step': step,
            'module_name': "Faculty Admission Wizard"
        })

    def post(self, request, *args, **kwargs):
        step = int(request.POST.get('step', 1))
        data = request.session.get('faculty_admission_data', {})
        
        current_data = request.POST.dict()
        data.update(current_data)
        request.session['faculty_admission_data'] = data

        form = self.get_form_for_step(step, request.POST, request.FILES)
        
        if form.is_valid():
            if step < 3:
                request.session['faculty_admission_step'] = step + 1
                return redirect(f"{request.path}?step={step + 1}")
            else:
                return self.finalize_admission(request, data, request.FILES)
        
        return render(request, self.template_name, {
            'form': form,
            'step': step,
            'module_name': "Faculty Admission Wizard"
        })

    def get_form_for_step(self, step, data=None, files=None):
        if step == 1: return FacultyStep1AccountForm(data)
        if step == 2: return FacultyStep2ProfessionalForm(data)
        if step == 3: return FacultyStep3DocumentForm(data, files)
        return FacultyStep1AccountForm(data)

    def finalize_admission(self, request, data, files):
        try:
            with transaction.atomic():
                user = User(
                    first_name=data.get('first_name'),
                    last_name=data.get('last_name'),
                    email=data.get('email'),
                    phone=data.get('phone'),
                    college_id=data.get('college'),
                    role=data.get('role')
                )
                user.set_password(data.get('password'))
                
                dept = Department.objects.get(id=data.get('academic_department'))
                user._academic_dept_context = dept
                user._academic_code_context = dept.dept_code if hasattr(dept, 'dept_code') else 'FAC'
                user.save()

                profile = user.faculty_profile
                profile.designation = data.get('designation')
                profile.qualification = data.get('qualification')
                profile.joining_date = data.get('joining_date')
                profile.department = dept
                profile.save()

                doc_map = {
                    'joining_letter': 'Joining Letter',
                    'resume': 'Resume',
                    'experience_certificate': 'Experience Certificate',
                    'qualification_proof': 'Qualification Proof',
                    'aadhar_card': 'Aadhar Card',
                    'other_document': 'Other Document'
                }
                for field_name, doc_type in doc_map.items():
                    file = files.get(field_name)
                    if file:
                        FacultyDocument.objects.create(
                            faculty=profile,
                            document_type=doc_type,
                            file=file,
                            file_name=file.name
                        )

            if 'faculty_admission_data' in request.session: del request.session['faculty_admission_data']
            if 'faculty_admission_step' in request.session: del request.session['faculty_admission_step']

            messages.success(request, f"Faculty {user.get_full_name()} admitted successfully!")
            return redirect('faculty_list')
        except Exception as e:
            messages.error(request, f"Error during faculty admission: {str(e)}")
            return redirect(f"{request.path}?step=1")

# --- FACULTY PROFILE MODULE ---
class FacultyProfileListView(RolePermissionMixin, ERPListView):
    model = FacultyProfile
    module_name = "Faculty"
    list_fields = ['employee_id', 'user', 'department', 'designation']
    create_url = 'admission/'
    required_permission = 'can_view_academic_registry'

    def test_func(self):
        if self.request.user.role == 'ADMISSION':
            return False
        return super().test_func()

class FacultyProfileCreateView(ERPCreateView):
    model = FacultyProfile
    def get(self, request, *args, **kwargs):
        return redirect('faculty_admission')

class FacultyProfileDetailView(RolePermissionMixin, ERPDetailView):
    model = FacultyProfile
    module_name = "Faculty"
    required_permission = 'can_view_academic_registry'

    def test_func(self):
        if self.request.user.role == 'ADMISSION':
            return False
        return super().test_func()

class FacultyProfileUpdateView(RolePermissionMixin, ERPUpdateView):
    model = FacultyProfile
    module_name = "Faculty"
    fields = ['employee_id', 'designation', 'qualification', 'joining_date']
    success_url = reverse_lazy('faculty_list')
    required_permission = 'can_manage_faculty'

# --- ACADEMIC SYLLABUS MODULE ---
class SyllabusProgressListView(RolePermissionMixin, ERPListView):
    model = SyllabusCoverage
    module_name = "Syllabus Progress"
    list_fields = ['allotment', 'percentage', 'last_updated']
    required_permission = 'can_view_academic_registry'
    template_name = 'dashboard/syllabus_progress_list.html'

    def test_func(self):
        if self.request.user.role == 'ADMISSION':
            return False
        return super().test_func()

    def get_queryset(self):
        # Auto-create missing SyllabusCoverage for all allotments
        try:
            allotments_without_coverage = SubjectAllotment.objects.filter(coverage__isnull=True)
            for allotment in allotments_without_coverage:
                SyllabusCoverage.objects.get_or_create(allotment=allotment)
        except Exception:
            pass

        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or not user.has_role_permission('can_view_dept_data'):
            return qs
        
        try:
            dept = user.faculty_profile.department
            return qs.filter(allotment__subject__branch__program__dept=dept)
        except:
            return qs.none()

class MySyllabusProgressListView(RolePermissionMixin, ERPListView):
    model = SyllabusCoverage
    module_name = "My Syllabus"
    list_fields = ['allotment__subject', 'percentage', 'last_updated']
    required_permission = 'can_view_academic_registry'
    template_name = 'dashboard/my_syllabus_list.html'

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        return user.is_superuser or str(user.role).upper() in ['ADMIN', 'SUB_ADMIN', 'HOD', 'TEACHER', 'FACULTY']

    def get_queryset(self):
        # Auto-create SyllabusCoverage for allotments of this faculty if they don't exist
        try:
            faculty = self.request.user.faculty_profile
            allotments_without_coverage = SubjectAllotment.objects.filter(faculty=faculty, coverage__isnull=True)
            for allotment in allotments_without_coverage:
                SyllabusCoverage.objects.get_or_create(allotment=allotment)
        except Exception:
            pass
        return super().get_queryset().filter(allotment__faculty__user=self.request.user)

class SyllabusProgressUpdateView(RolePermissionMixin, ERPUpdateView):
    model = SyllabusCoverage
    module_name = "Update Progress"
    fields = ['topics_covered']
    required_permission = 'can_view_academic_registry'
    template_name = 'dashboard/syllabus_progress_update.html'
    success_url = reverse_lazy('my_syllabus_progress')

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        return user.is_superuser or str(user.role).upper() in ['ADMIN', 'SUB_ADMIN', 'HOD', 'TEACHER', 'FACULTY']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        role_upper = str(user.role).upper()
        if role_upper in ['TEACHER', 'FACULTY']:
            return qs.filter(allotment__faculty__user=user)
        elif role_upper == 'HOD':
            try:
                dept = user.faculty_profile.department
                return qs.filter(allotment__subject__branch__program__dept=dept)
            except Exception:
                return qs.none()
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subject = self.object.allotment.subject
        context['topics'] = subject.topics.all()
        context['completed_topics'] = self.object.completed_topics.all()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        topic_ids = request.POST.getlist('topics')
        self.object.completed_topics.set(topic_ids)
        self.object.topics_covered = request.POST.get('topics_covered', '')
        self.object.update_percentage()
        return redirect(self.success_url)

class SubjectTopicCreateView(RolePermissionMixin, ERPCreateView):
    model = SubjectTopic
    form_class = SyllabusTopicForm
    module_name = "Subject Topic"
    required_permission = 'can_manage_subjects'
    success_url = reverse_lazy('subject_list')

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser or user.has_role_permission('can_manage_subjects'):
            return True
        if str(user.role).upper() in ['TEACHER', 'FACULTY']:
            subject_id = self.request.GET.get('subject') or self.request.POST.get('subject')
            if subject_id:
                return SubjectAllotment.objects.filter(faculty__user=user, subject_id=subject_id).exists()
        return False

    def get_initial(self):
        initial = super().get_initial()
        subject_id = self.request.GET.get('subject')
        if subject_id:
            initial['subject'] = subject_id
        return initial

    def get_success_url(self):
        coverage_id = self.request.GET.get('coverage') or self.request.POST.get('coverage')
        if coverage_id:
            from django.urls import reverse
            return reverse('syllabus_progress_update', kwargs={'pk': coverage_id})
        return super().get_success_url()

class DepartmentTimetableView(RolePermissionMixin, ERPListView):
    model = SubjectSchedule
    module_name = "Dept. Timetable"
    template_name = 'faculty/timetable.html'
    required_permission = 'can_view_academic_registry'

    def test_func(self):
        if self.request.user.role == 'ADMISSION':
            return False
        return super().test_func()

    def get_queryset(self):
        user = self.request.user
        try:
            dept = user.faculty_profile.department
            branch_id = self.request.GET.get('branch')
            semester = self.request.GET.get('semester')
            
            qs = SubjectSchedule.objects.filter(
                allotment__subject__branch__program__dept=dept
            ).select_related('allotment__subject', 'allotment__faculty__user')
            
            if branch_id:
                qs = qs.filter(allotment__subject__branch_id=branch_id)
            if semester:
                qs = qs.filter(allotment__subject__semester=semester)
                
            return qs.order_by('day', 'start_time')
        except Exception as e:
            return SubjectSchedule.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        
        # Aggregate Weekly Stats
        context['total_classes'] = qs.count()
        context['theory_count'] = qs.filter(session_type='Theory').count()
        context['practical_count'] = qs.filter(session_type='Lab').count()
        context['free_slots_mock'] = 6 * 6 - context['total_classes'] # Assumption 6 periods/day
        
        timetable_data = []
        for day_val, day_name in SubjectSchedule.DAYS:
            day_sessions = [s for s in qs if s.day == day_val]
            timetable_data.append({
                'val': day_val,
                'name': day_name,
                'sessions': day_sessions
            })
            
        context['timetable_data'] = timetable_data
        context['view_type'] = 'departmental'
        
        user = self.request.user
        try:
            dept = user.faculty_profile.department
            context['branches'] = Branch.objects.filter(program__dept=dept)
            context['semesters'] = range(1, 9)
            # Add permission flag for management
            context['can_manage_timetable'] = user.role in ['ADMIN', 'HOD']
        except:
            context['branches'] = Branch.objects.none()
            context['can_manage_timetable'] = user.role == 'ADMIN'
            
        return context

class GetFilteredSubjectsView(RolePermissionMixin, View):
    required_permission = 'can_view_academic_registry'
    
    def get(self, request):
        branch_id = request.GET.get('branch')
        semester = request.GET.get('semester')
        
        user = request.user
        qs = Subject.objects.all()
        
        # Scope by department if not superuser
        if not user.is_superuser:
            try:
                dept = user.faculty_profile.department
                qs = qs.filter(branch__program__dept=dept)
            except:
                pass

        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if semester:
            qs = qs.filter(semester=semester)
            
        data = [
            {'id': s.id, 'label': f"{s.subject_name} ({s.subject_code})"}
            for s in qs
        ]
        return JsonResponse({'subjects': data})

class GetFilteredAllotmentsView(RolePermissionMixin, View):
    required_permission = 'can_view_academic_registry'
    
    def get(self, request):
        branch_id = request.GET.get('branch')
        semester = request.GET.get('semester')
        
        user = request.user
        qs = SubjectAllotment.objects.all()
        
        # Scope by department if not superuser
        if not user.is_superuser:
            try:
                dept = user.faculty_profile.department
                qs = qs.filter(faculty__department=dept)
            except:
                pass

        if branch_id:
            qs = qs.filter(subject__branch_id=branch_id)
        if semester:
            qs = qs.filter(subject__semester=semester)
            
        data = [
            {'id': a.id, 'label': f"{a.subject.subject_name} ({a.subject.subject_code}) - {a.faculty.user.get_full_name()}"}
            for a in qs.select_related('subject', 'faculty__user')
        ]
        return JsonResponse({'allotments': data})

class SubjectScheduleCreateView(RolePermissionMixin, ERPCreateView):
    model = SubjectSchedule
    form_class = SubjectScheduleCreateForm
    module_name = "Timetable Session"
    required_permission = 'can_manage_subjects'
    success_url = reverse_lazy('dept_timetable')
    template_name = 'faculty/session_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        try:
            kwargs['department'] = self.request.user.faculty_profile.department
        except:
            pass
        return kwargs

class SubjectScheduleUpdateView(RolePermissionMixin, ERPUpdateView):
    model = SubjectSchedule
    form_class = SubjectScheduleForm
    module_name = "Timetable Session"
    required_permission = 'can_manage_subjects'
    success_url = reverse_lazy('dept_timetable')
    template_name = 'faculty/session_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        try:
            kwargs['department'] = self.request.user.faculty_profile.department
        except:
            pass
        return kwargs

class SubjectScheduleDeleteView(RolePermissionMixin, View):
    required_permission = 'can_manage_subjects'
    def post(self, request, pk):
        schedule = SubjectSchedule.objects.get(pk=pk)
        schedule.delete()
        messages.success(request, "Session removed from timetable.")
        return redirect('dept_timetable')

class MyTimetableView(RolePermissionMixin, ERPListView):
    model = SubjectSchedule
    template_name = 'faculty/timetable.html'
    required_permission = None

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        allowed_roles = ['ADMIN', 'SUB_ADMIN', 'HOD', 'FACULTY', 'TEACHER']
        return str(user.role).upper() in allowed_roles

    def get_queryset(self):
        user = self.request.user
        try:
            faculty = user.faculty_profile
            return SubjectSchedule.objects.filter(
                allotment__faculty=faculty
            ).select_related('allotment__subject', 'allotment__faculty__user').order_by('day', 'start_time')
        except:
            return SubjectSchedule.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        
        # Aggregate Weekly Stats
        context['total_classes'] = qs.count()
        context['theory_count'] = qs.filter(session_type='Theory').count()
        context['practical_count'] = qs.filter(session_type='Lab').count()
        context['free_slots_mock'] = 4 # Mock as per UI
        
        timetable_data = []
        for day_val, day_name in SubjectSchedule.DAYS:
            day_sessions = [s for s in qs if s.day == day_val]
            timetable_data.append({
                'val': day_val,
                'name': day_name,
                'is_today': day_val == (timezone.now().isoweekday()),
                'sessions': day_sessions
            })
            
        context['timetable_data'] = timetable_data
        context['view_type'] = 'personal'
        return context

# --- ATTENDANCE MANAGEMENT ---

class MarkAttendanceView(RolePermissionMixin, View):
    required_permission = None
    template_name = 'faculty/mark_attendance.html'

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        # Only allow Admin, HOD, Teacher, and Faculty roles
        allowed_roles = ['ADMIN', 'SUB_ADMIN', 'HOD', 'FACULTY', 'TEACHER']
        return str(user.role).upper() in allowed_roles

    def get_context_data(self, user, class_id=None, subject_id=None, date=None):
        """Helper to prepare filtered data for the view."""
        # 1. Fetch available classes based on role and branch duration
        from apps.core.models import Branch
        branches = Branch.objects.all()
        if user.role != 'ADMIN':
            try:
                dept = user.faculty_profile.department
                branches = branches.filter(program__dept=dept).select_related('program__dept')
            except:
                pass
        
        # Get all active combinations from students to know which sections actually exist
        active_student_groups = Student.objects.filter(status='active').values(
            'branch_id', 'semester', 'section'
        ).distinct()
        
        # Build a map for quick lookup: branch_id -> semester -> list of sections
        group_map = {}
        for group in active_student_groups:
            b_id = group['branch_id']
            sem = group['semester']
            sec = group['section']
            if b_id not in group_map: group_map[b_id] = {}
            if sem not in group_map[b_id]: group_map[b_id][sem] = []
            if sec not in group_map[b_id][sem]:
                group_map[b_id][sem].append(sec)

        class_list = []
        for branch in branches.order_by('branch_code'):
            # Show all semesters based on branch duration (e.g., 4 years -> 8 semesters)
            max_semester = (branch.duration_years or 4) * 2
            for sem in range(1, max_semester + 1):
                # Identify sections for this branch/semester
                sections = group_map.get(branch.id, {}).get(sem, [])
                
                # If no existing sections found for this specific semester level, 
                # default to 'A' to satisfy the "show all according to duration" requirement.
                if not sections:
                    sections = ['A']
                
                for sec in sorted(sections):
                    class_list.append({
                        'id': f"{branch.id}:{sem}:{sec}",
                        'label': f"{branch.branch_code} - {sem}th Sem (Sec {sec})"
                    })

        # 2. Handle selections
        subjects = []
        students = []
        selected_class = None
        selected_subject = None
        
        if class_id:
            try:
                parts = class_id.split(':')
                if len(parts) == 3:
                    b_id, sem, sec = parts
                    selected_class = next((c for c in class_list if c['id'] == class_id), None)
                    
                    # Fetch subjects for this class
                    subject_qs = Subject.objects.filter(branch_id=b_id, semester=sem)
                    
                    # Admins, HODs, and Teachers should see ALL subjects for the selected semester/branch
                    if user.role not in ['ADMIN', 'HOD', 'FACULTY', 'TEACHER']:
                        # Other staff (if any) are narrowed down to their own allotments
                        allotted_subject_ids = SubjectAllotment.objects.filter(
                            faculty__user=user,
                            subject__branch_id=b_id,
                            subject__semester=sem
                        ).values_list('subject_id', flat=True)
                        
                        # Only apply filter if they actually have specific allotments for this branch/sem
                        if allotted_subject_ids.exists():
                            subject_qs = subject_qs.filter(id__in=allotted_subject_ids)
                    
                    subjects = subject_qs.distinct()

                    if subject_id:
                        selected_subject = subjects.filter(id=subject_id).first()
                    
                    # Fetch students immediately when class is selected
                    students = list(Student.objects.filter(
                        branch_id=b_id, semester=sem, section=sec, status='active'
                    ).select_related('user').annotate(
                        identifier=Coalesce('roll_number', 'enrollment_number')
                    ).order_by('identifier'))
            except (ValueError, IndexError):
                pass
        
        # 3. Check for existing attendance records
        attendance_record = {}
        existing_session_metadata = None
        if selected_class and selected_subject and date:
            try:
                _, _, sec = class_id.split(':')
                # Query established records for this session
                attendance_qs = StudentAttendance.objects.filter(
                    allotment__subject=selected_subject,
                    date=date,
                    section=sec
                ).select_related('allotment')
                
                if attendance_qs.exists():
                    # Pick metadata from the first record (they all share the same session info)
                    first_rec = attendance_qs.first()
                    existing_session_metadata = {
                        'session_type': first_rec.session_type,
                        'remarks': first_rec.remarks,
                        'marked_by': first_rec.marked_by
                    }
                    
                    attendance_record = {
                        str(att.student_id): att.status 
                        for att in attendance_qs
                    }
                    # Attach existing status to student objects for easier template access
                    for student in students:
                        student.existing_status = attendance_record.get(str(student.id))
            except:
                pass
                
        return {
            'class_list': class_list,
            'subjects': subjects,
            'class_id': class_id,
            'subject_id': subject_id,
            'students': students,
            'selected_class': selected_class,
            'selected_subject': selected_subject,
            'attendance_record': attendance_record,
            'existing_session': existing_session_metadata, # Keep key as existing_session for template compatibility
        }

    def get(self, request, *args, **kwargs):
        class_id = request.GET.get('class_batch')
        subject_id = request.GET.get('subject')
        date = request.GET.get('date', timezone.now().date().isoformat())
        
        # Future date validation
        try:
            if timezone.datetime.strptime(date, '%Y-%m-%d').date() > timezone.now().date():
                messages.warning(request, "Future date attendance marking is not allowed.")
                date = timezone.now().date().isoformat()
        except:
            pass

        context = self.get_context_data(request.user, class_id, subject_id, date)
        context.update({
            'date': date,
            'today_date': timezone.now().date().isoformat(),
            'module_name': "Daily Attendance",
        })

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Handle AJAX Filtering
            subjects_data = [
                {'id': s.id, 'name': s.subject_name, 'code': s.subject_code} 
                for s in context['subjects']
            ]
            html_content = render_to_string('faculty/partials/attendance_sheet.html', context, request=request)
            return JsonResponse({
                'subjects': subjects_data,
                'html': html_content,
                'selected_subject_id': subject_id
            })

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        class_id = request.POST.get('class_batch')
        subject_id = request.POST.get('subject')
        date = request.POST.get('date')
        session_type = request.POST.get('session_type', 'Theory')
        remarks = request.POST.get('remarks', '')
        
        if not all([class_id, subject_id, date]):
            messages.error(request, "Please select all required fields.")
            return redirect('mark_attendance')

        # Future date validation
        try:
            if timezone.datetime.strptime(date, '%Y-%m-%d').date() > timezone.now().date():
                messages.error(request, "Cannot mark attendance for future dates.")
                return redirect('mark_attendance')
        except:
            pass

        try:
            parts = class_id.split(':')
            if len(parts) != 3:
                raise ValueError("Invalid class selection.")
            b_id, sem, sec = parts
            
            # 2. Resolve Allotment
            # For Teachers, we use their own allotment.
            # For Admins/HODs, we find the existing allotment for the subject.
            allotment = None
            if request.user.role in ['ADMIN', 'HOD']:
                allotment = SubjectAllotment.objects.filter(subject_id=subject_id).first()
                
            if not allotment:
                # Fallback to personal allotment
                faculty_profile = getattr(request.user, 'faculty_profile', None)
                
                # Auto-provision a Faculty Profile for Admins if missing
                if not faculty_profile and request.user.role == 'ADMIN':
                    faculty_profile = FacultyProfile.objects.create(
                        user=request.user,
                        employee_id=f"ADMIN-{request.user.id}",
                        designation="System Administrator"
                    )

                if not faculty_profile:
                    messages.error(request, "Access Denied: Your account is not linked to a Faculty Profile and no existing allotment was found for this subject.")
                    return redirect('mark_attendance')
                
                allotment, _ = SubjectAllotment.objects.get_or_create(
                    faculty=faculty_profile,
                    subject_id=subject_id,
                    defaults={'session': '2025-26'}
                )

            with transaction.atomic():
                attendance_marked = False
                for key, value in request.POST.items():
                    if key.startswith('status_'):
                        student_id = key.split('_')[1]
                        
                        StudentAttendance.objects.update_or_create(
                            student_id=student_id,
                            allotment=allotment,
                            date=date,
                            section=sec,
                            session_type=session_type,
                            defaults={
                                'status': value,
                                'marked_by': request.user,
                                'remarks': remarks
                            }
                        )
                        attendance_marked = True
                
                if attendance_marked:
                    messages.success(request, f"Attendance for {allotment.subject.subject_name} ({date}) saved successfully.")
                else:
                    messages.warning(request, "No students marked.")
        except Exception as e:
            messages.error(request, f"Error saving attendance: {str(e)}")

        return redirect(f"{reverse_lazy('mark_attendance')}?class_batch={class_id}&subject={subject_id}&date={date}")

# --- SUBJECT ALLOTMENT MODULE ---
SubjectScheduleFormSet = inlineformset_factory(
    SubjectAllotment, SubjectSchedule,
    form=SubjectScheduleForm,
    extra=1, can_delete=True
)

class SubjectAllotmentListView(RolePermissionMixin, ERPListView):
    model = SubjectAllotment
    module_name = "Subject Allotment"
    list_fields = ['faculty', 'subject', 'semester', 'session', 'session_count']
    required_permission = 'can_view_subjects'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or not user.has_role_permission('can_view_dept_data'):
            return qs
        try:
            dept = user.faculty_profile.department
            return qs.filter(faculty__department=dept)
        except:
            return qs.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # Enable management buttons for HODs and registry managers
        can_manage = user.is_superuser or user.role == 'HOD' or \
                     user.has_role_permission('can_manage_subjects') or \
                     user.has_role_permission('can_manage_academic_registry')
        
        context['can_add'] = can_manage
        context['can_edit'] = can_manage
        return context

class SubjectAllotmentDetailView(RolePermissionMixin, ERPDetailView):
    model = SubjectAllotment
    module_name = "Subject Allotment"
    required_permission = 'can_view_academic_registry'

class SubjectAllotmentCreateView(RolePermissionMixin, ERPCreateView):
    model = SubjectAllotment
    module_name = "Subject Allotment"
    template_name = 'generic/form.html'
    form_class = SubjectAllotmentForm
    success_url = reverse_lazy('subject_allotment_list')
    required_permission = 'can_manage_subjects'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            formset = SubjectScheduleFormSet(self.request.POST)
        else:
            formset = SubjectScheduleFormSet()
        
        data['inlines'] = [{
            'title': 'Weekly Sessions',
            'formset': formset,
            'icon': 'fa-calendar-clock'
        }]
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        inlines = context.get('inlines', [])
        formset = inlines[0]['formset'] if inlines else None
        
        if formset and formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                formset.instance = self.object
                formset.save()
            return super().form_valid(form)
        elif not formset:
            return super().form_valid(form)
        else:
            return self.form_invalid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        user = self.request.user
        if not user.is_superuser:
            try:
                kwargs['department'] = user.faculty_profile.department
            except:
                pass
        return kwargs

class SubjectAllotmentUpdateView(RolePermissionMixin, ERPUpdateView):
    model = SubjectAllotment
    module_name = "Subject Allotment"
    template_name = 'generic/form.html'
    form_class = SubjectAllotmentForm
    success_url = reverse_lazy('subject_allotment_list')
    required_permission = 'can_manage_subjects'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            formset = SubjectScheduleFormSet(self.request.POST, instance=self.object)
        else:
            formset = SubjectScheduleFormSet(instance=self.object)
        
        data['inlines'] = [{
            'title': 'Weekly Sessions',
            'formset': formset,
            'icon': 'fa-calendar-clock'
        }]
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        inlines = context.get('inlines', [])
        formset = inlines[0]['formset'] if inlines else None
        
        with transaction.atomic():
            self.object = form.save()
            if formset and formset.is_valid():
                formset.instance = self.object
                formset.save()
            elif formset:
                return self.form_invalid(form)
                
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        user = self.request.user
        if not user.is_superuser:
            try:
                kwargs['department'] = user.faculty_profile.department
            except:
                pass
        return kwargs

class SubjectAllotmentDeleteView(RolePermissionMixin, View):
    required_permission = 'can_manage_subjects'
    def post(self, request, pk):
        allotment = SubjectAllotment.objects.get(pk=pk)
        if not request.user.is_superuser:
            try:
                if allotment.faculty.department != request.user.faculty_profile.department:
                    messages.error(request, "Permission Denied: You can only delete allotments for your department.")
                    return redirect('subject_allotment_list')
            except:
                pass
        
        allotment.delete()
        messages.success(request, "Subject allotment removed successfully.")
        return redirect('subject_allotment_list')

# --- FACULTY PROFESSIONAL HUB ---
class MyResearchPublicationListView(RolePermissionMixin, ERPListView):
    model = ResearchPublication
    module_name = "Research Portfolio"
    list_fields = ['title', 'pub_type', 'publication_date']
    required_permission = 'can_view_academic_registry'

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        return user.is_superuser or str(user.role).upper() in ['ADMIN', 'SUB_ADMIN', 'HOD', 'TEACHER', 'FACULTY']

    def get_queryset(self):
        return super().get_queryset().filter(faculty__user=self.request.user)

class MyFacultyDocumentListView(RolePermissionMixin, ERPListView):
    model = FacultyDocument
    module_name = "Digital Cabinet"
    list_fields = ['document_type', 'file_name', 'uploaded_at', 'verified']
    required_permission = 'can_view_academic_registry'

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        return user.is_superuser or str(user.role).upper() in ['ADMIN', 'SUB_ADMIN', 'HOD', 'TEACHER', 'FACULTY']

    def get_queryset(self):
        return super().get_queryset().filter(faculty__user=self.request.user)

# --- STUDENT LEAVE MANAGEMENT ---
class StudentLeaveApprovalListView(RolePermissionMixin, View):
    required_permission = 'can_view_academic_registry'
    template_name = 'dashboard/student_leave_approvals.html'

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        return user.is_superuser or str(user.role).upper() in ['ADMIN', 'SUB_ADMIN', 'HOD', 'TEACHER', 'FACULTY']

    def get(self, request, *args, **kwargs):
        user = request.user
        try:
            faculty = user.faculty_profile
        except:
            messages.error(request, "You do not have a faculty profile to manage leaves.")
            return redirect('dashboard')

        # Filter leaves where this faculty is the mentor
        qs = StudentLeave.objects.filter(mentor=faculty)
        
        # Filtering logic
        status_filter = request.GET.get('status', 'Pending')
        if status_filter != 'all':
            qs = qs.filter(status=status_filter)
        
        search_query = request.GET.get('search', '')
        if search_query:
            qs = qs.filter(student__user__first_name__icontains=search_query) | \
                 qs.filter(student__user__last_name__icontains=search_query) | \
                 qs.filter(student__roll_number__icontains=search_query)

        # Basic stats
        stats = {
            'pending': StudentLeave.objects.filter(mentor=faculty, status='Pending').count(),
            'approved': StudentLeave.objects.filter(mentor=faculty, status='Approved').count(),
            'rejected': StudentLeave.objects.filter(mentor=faculty, status='Rejected').count(),
            'on_leave_today': StudentLeave.objects.filter(
                mentor=faculty, 
                status='Approved',
                start_date__lte=timezone.now().date(),
                end_date__gte=timezone.now().date()
            ).count()
        }

        context = {
            'module_name': "Leave Approvals",
            'leaves': qs,
            'stats': stats,
            'current_status': status_filter
        }
        return render(request, self.template_name, context)

class StudentLeaveActionView(RolePermissionMixin, View):
    required_permission = 'can_view_academic_registry' # Mentors usually have this

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        return user.is_superuser or str(user.role).upper() in ['ADMIN', 'SUB_ADMIN', 'HOD', 'TEACHER', 'FACULTY']

    def post(self, request, pk, action):
        try:
            leave = StudentLeave.objects.get(pk=pk, mentor=request.user.faculty_profile)
        except StudentLeave.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Leave application not found.'}, status=404)

        remarks = ''
        if request.content_type == 'application/json':
            import json
            try:
                data = json.loads(request.body)
                remarks = data.get('remarks', '')
            except json.JSONDecodeError:
                pass
        else:
            remarks = request.POST.get('remarks', '')
        
        if action == 'approve':
            leave.status = 'Approved'
        elif action == 'reject':
            leave.status = 'Rejected'
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid action.'}, status=400)

        leave.mentor_remarks = remarks
        leave.save()
        
        status_color = 'success' if action == 'approve' else 'danger'
        messages.success(request, f"Leave application for {leave.student.user.get_full_name()} has been {action}d.")
        
        return JsonResponse({
            'status': 'success', 
            'new_status': leave.status,
            'message': f"Application {action}d successfully."
        })

from .models import FacultyLeave, FacultyLeaveBalance

class FacultyMyLeaveListView(RolePermissionMixin, View):
    required_permission = 'can_view_my_leaves'
    template_name = 'leaves/my_leaves.html'

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        return user.is_superuser or str(user.role).upper() in ['ADMIN', 'SUB_ADMIN', 'HOD', 'TEACHER', 'FACULTY']

    def get(self, request, *args, **kwargs):
        try:
            faculty = request.user.faculty_profile
        except FacultyProfile.DoesNotExist:
            messages.error(request, "Faculty profile missing. Please contact administrator.")
            return redirect('dashboard')
            
        leaves = FacultyLeave.objects.filter(faculty=faculty).order_by('-created_at')
        
        # Get or Create Balance for current year
        current_year = timezone.now().year
        balances, _ = FacultyLeaveBalance.objects.get_or_create(
            faculty=faculty, 
            year=current_year
        )
        
        context = {
            'module_name': "My Leave Desk",
            'leaves': leaves,
            'balances': balances,
            'user': request.user
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        try:
            faculty = request.user.faculty_profile
        except FacultyProfile.DoesNotExist:
            messages.error(request, "Faculty profile missing.")
            return redirect('dashboard')
            
        action = request.POST.get('action')
        
        if action == 'cancel':
            leave_id = request.POST.get('leave_id')
            leave = get_object_or_404(FacultyLeave, id=leave_id, faculty=faculty, status='Pending')
            leave.delete()
            messages.success(request, "Leave application cancelled successfully.")
            
        elif action == 'apply':
            leave_type = request.POST.get('leave_type')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            reason = request.POST.get('reason')
            alt_arrangement = request.POST.get('alt_arrangement')
            attachment = request.FILES.get('attachment')
            
            FacultyLeave.objects.create(
                faculty=faculty,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                reason=reason,
                alt_arrangement=alt_arrangement,
                attachment=attachment
            )
            messages.success(request, "Leave application submitted and awaiting approval.")
            
        return redirect('faculty_my_leaves')


class EnterMarksView(RolePermissionMixin, View):
    required_permission = None # Handled inside test_func and role checks
    template_name = 'faculty/enter_marks.html'

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        # Only allow Admin, HOD, Teacher, and Faculty roles
        allowed_roles = ['ADMIN', 'SUB_ADMIN', 'HOD', 'FACULTY', 'TEACHER']
        return str(user.role).upper() in allowed_roles

    def get_context_data(self, user, class_id=None, subject_id=None, assessment_type=None):
        from apps.core.models import Branch, Subject
        from apps.students.models import Student, MidTermMark
        from apps.faculty.models import SubjectAllotment

        # 1. Fetch available classes
        branches = Branch.objects.all()
        if user.role not in ['ADMIN', 'SUB_ADMIN']:
            try:
                dept = user.faculty_profile.department
                branches = branches.filter(program__dept=dept).select_related('program__dept')
            except:
                pass

        active_student_groups = Student.objects.filter(status='active').values(
            'branch_id', 'semester', 'section'
        ).distinct()

        group_map = {}
        for group in active_student_groups:
            b_id = group['branch_id']
            sem = group['semester']
            sec = group['section']
            if b_id not in group_map: group_map[b_id] = {}
            if sem not in group_map[b_id]: group_map[b_id][sem] = []
            if sec not in group_map[b_id][sem]:
                group_map[b_id][sem].append(sec)

        class_list = []
        for branch in branches.order_by('branch_code'):
            max_semester = (branch.duration_years or 4) * 2
            for sem in range(1, max_semester + 1):
                sections = group_map.get(branch.id, {}).get(sem, [])
                if not sections:
                    sections = ['A']
                for sec in sorted(sections):
                    class_list.append({
                        'id': f"{branch.id}:{sem}:{sec}",
                        'label': f"{branch.branch_code} - {sem}th Sem (Sec {sec})"
                    })

        # 2. Handle Selections
        subjects = []
        students = []
        selected_class = None
        selected_subject = None
        marks_map = {}
        max_marks = 30 # default Max Marks for Mid-terms

        if class_id:
            try:
                parts = class_id.split(':')
                if len(parts) == 3:
                    b_id, sem, sec = parts
                    selected_class = next((c for c in class_list if c['id'] == class_id), None)
                    
                    # Fetch subjects for this class
                    subject_qs = Subject.objects.filter(branch_id=b_id, semester=sem)
                    
                    if user.role not in ['ADMIN', 'SUB_ADMIN', 'HOD']:
                        # Filter subjects to teacher allotments
                        allotted_subject_ids = SubjectAllotment.objects.filter(
                            faculty__user=user,
                            subject__branch_id=b_id,
                            subject__semester=sem
                        ).values_list('subject_id', flat=True)
                        
                        if allotted_subject_ids.exists():
                            subject_qs = subject_qs.filter(id__in=allotted_subject_ids)
                    
                    subjects = subject_qs.distinct()

                    if subject_id:
                        selected_subject = subjects.filter(id=subject_id).first()
                    
                    # Fetch active students
                    students = list(Student.objects.filter(
                        branch_id=b_id, semester=sem, section=sec, status='active'
                    ).select_related('user').order_by('roll_number', 'enrollment_number'))

                    # Fetch marks
                    if selected_subject and assessment_type:
                        marks_qs = MidTermMark.objects.filter(
                            student__in=students,
                            subject=selected_subject,
                            mid_term_type=assessment_type
                        )
                        if marks_qs.exists():
                            max_marks = int(marks_qs.first().max_marks)
                        marks_map = {m.student_id: m for m in marks_qs}
                        
                        # Populate student's mark value
                        for s in students:
                            m_record = marks_map.get(s.id)
                            s.obtained_marks = m_record.obtained_marks if m_record else ""
                            s.remarks = m_record.remarks if m_record else ""
            except Exception as e:
                print(f"Error filtering enter marks: {e}")
                pass

        return {
            'class_list': class_list,
            'subjects': subjects,
            'class_id': class_id,
            'subject_id': subject_id,
            'assessment_type': assessment_type or 'midterm1',
            'students': students,
            'selected_class': selected_class,
            'selected_subject': selected_subject,
            'max_marks': max_marks,
        }

    def get(self, request, *args, **kwargs):
        class_id = request.GET.get('class_batch')
        subject_id = request.GET.get('subject')
        assessment_type = request.GET.get('assessment_type', 'midterm1')

        context = self.get_context_data(request.user, class_id, subject_id, assessment_type)
        context.update({
            'module_name': "Marks Entry",
        })

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Handle AJAX Filtering (updating subject choices when class selection changes)
            subjects_data = [
                {'id': s.id, 'name': s.subject_name, 'code': s.subject_code} 
                for s in context['subjects']
            ]
            return JsonResponse({
                'subjects': subjects_data,
                'selected_subject_id': subject_id
            })

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        class_id = request.POST.get('class_batch')
        subject_id = request.POST.get('subject')
        assessment_type = request.POST.get('assessment_type')
        max_marks_val = request.POST.get('max_marks', '30')

        if not all([class_id, subject_id, assessment_type]):
            messages.error(request, "Please select all required fields.")
            return redirect('enter_marks')

        try:
            max_marks = float(max_marks_val)
        except ValueError:
            max_marks = 30.0

        from apps.students.models import Student, MidTermMark
        from apps.core.models import Subject

        try:
            parts = class_id.split(':')
            if len(parts) != 3:
                raise ValueError("Invalid class selection.")
            b_id, sem, sec = parts

            students = Student.objects.filter(branch_id=b_id, semester=sem, section=sec, status='active')

            with transaction.atomic():
                saved_count = 0
                for s in students:
                    mark_key = f"marks_{s.id}"
                    remarks_key = f"remarks_{s.id}"
                    
                    mark_val = request.POST.get(mark_key)
                    remarks_val = request.POST.get(remarks_key, '')

                    if mark_val is not None and mark_val.strip() != "":
                        try:
                            obtained_marks = float(mark_val)
                            MidTermMark.objects.update_or_create(
                                student=s,
                                subject_id=subject_id,
                                mid_term_type=assessment_type,
                                defaults={
                                    'obtained_marks': obtained_marks,
                                    'max_marks': max_marks,
                                    'remarks': remarks_val
                                }
                            )
                            saved_count += 1
                        except ValueError:
                            pass
                    else:
                        # If blank, delete existing mark record (Absent)
                        MidTermMark.objects.filter(
                            student=s,
                            subject_id=subject_id,
                            mid_term_type=assessment_type
                        ).delete()

                messages.success(request, f"Successfully saved marks for {saved_count} students.")
        except Exception as e:
            messages.error(request, f"Error saving marks: {str(e)}")

        return redirect(f"{request.path}?class_batch={class_id}&subject={subject_id}&assessment_type={assessment_type}")

