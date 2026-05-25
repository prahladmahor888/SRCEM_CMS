from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.db import models
from django.http import HttpResponse, HttpResponseRedirect
import csv
from apps.core.models import (
    PublicNotice, HeroSlide, CollegeEvent, HomeProgram, GalleryItem, Recruiter, CollegeStat, AboutSectionConfig,
    PlacementConfig, PlacementAchiever, PlacementTrainingFeature, PlacementProcessStep
)

class PublicHomeView(ListView):
    template_name = 'home.html'
    model = PublicNotice
    context_object_name = 'notices'
    
    def get_queryset(self):
        return PublicNotice.objects.filter(is_active=True).order_by('-created_at')[:10]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filter popup notices specifically
        popup_notices = PublicNotice.objects.filter(is_active=True, is_popup=True).order_by('-created_at')
        context['popup_notice'] = popup_notices.first()
        context['popup_notices'] = popup_notices
        
        # Categorized Notices & Circulars
        context['announcements'] = PublicNotice.objects.filter(is_active=True, notice_type='announcement').order_by('-created_at')[:10]
        context['circulars'] = PublicNotice.objects.filter(is_active=True, notice_type='circular').order_by('-created_at')[:10]
        
        # Hero Slides
        context['hero_slides'] = HeroSlide.objects.filter(is_active=True).order_by('order', 'id')
        
        # College Events
        context['events'] = CollegeEvent.objects.filter(is_active=True).order_by('-event_date')[:6]
        
        # Programs
        context['programs'] = HomeProgram.objects.filter(is_active=True).order_by('order', 'id')
        
        # Recruiters
        context['recruiters'] = Recruiter.objects.filter(is_active=True).order_by('order', 'name')
        
        # College Stats
        context['stats'] = CollegeStat.objects.filter(is_active=True).order_by('order', 'id')
        
        # About Section Configuration
        context['about_config'] = AboutSectionConfig.objects.filter(is_active=True).first()
        
        # Gallery Items
        context['gallery'] = GalleryItem.objects.filter(is_active=True).order_by('order', '-created_at')[:12]
        
        return context

class AboutUsView(TemplateView):
    template_name = 'about_us.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['about_config'] = AboutSectionConfig.objects.filter(is_active=True).first()
        context['stats'] = CollegeStat.objects.filter(is_active=True).order_by('order', 'id')
        return context

class PlacementsView(TemplateView):
    template_name = 'placements.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['placement_config'] = PlacementConfig.objects.filter(is_active=True).first()
        context['achievers'] = PlacementAchiever.objects.filter(is_active=True).order_by('order', '-package', 'id')
        context['training_features'] = PlacementTrainingFeature.objects.filter(is_active=True).order_by('order', 'id')
        context['process_steps'] = PlacementProcessStep.objects.filter(is_active=True).order_by('step_number', 'id')
        context['recruiters'] = Recruiter.objects.filter(is_active=True).order_by('order', 'name')
        return context


class PlacementListView(ListView):
    model = PlacementAchiever
    template_name = 'placements_list.html'
    context_object_name = 'achievers'
    paginate_by = 16

    def get_queryset(self):
        queryset = PlacementAchiever.objects.filter(is_active=True).order_by('order', '-package', 'id')
        
        # Search query
        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                models.Q(student_name__icontains=q) | 
                models.Q(company_name__icontains=q)
            )

        # Branch filter
        branch = self.request.GET.get('branch', '').strip()
        if branch:
            queryset = queryset.filter(branch=branch)

        # Year filter
        year = self.request.GET.get('year', '').strip()
        if year:
            try:
                queryset = queryset.filter(placed_year=int(year))
            except ValueError:
                pass

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get dynamic list of active branches and years for filter dropdowns
        all_achievers = PlacementAchiever.objects.filter(is_active=True)
        context['branches'] = sorted(list(set(all_achievers.values_list('branch', flat=True))))
        context['years'] = sorted(list(set(all_achievers.values_list('placed_year', flat=True))), reverse=True)
        
        # Pass current search state back to template
        context['query'] = self.request.GET.get('q', '').strip()
        context['selected_branch'] = self.request.GET.get('branch', '').strip()
        context['selected_year'] = self.request.GET.get('year', '').strip()
        
        # Also include recruiter context if needed, or core config for styling/branding
        context['placement_config'] = PlacementConfig.objects.filter(is_active=True).first()
        
        return context


class ERPBaseMixin(LoginRequiredMixin):
    """Base mixin for all ERP views to handle common context and role logic."""
    page_title = ""
    module_name = "" # e.g., 'Student', 'Faculty'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.page_title or f"{self.module_name} Management"
        context['module_name'] = self.module_name
        return context

from django.contrib import messages

class RolePermissionMixin(UserPassesTestMixin):
    """View Mixin to check for a specific Role-Based Permission."""
    required_permission = None

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        
        # Superusers bypass checks
        if self.request.user.is_superuser:
            return True
            
        # Students are globally restricted from all Registry views 
        # unless they are viewing their OWN user record (specific logic elsewhere)
        # Students can access their own data views
        if hasattr(self.request.user, 'is_student_user') and self.request.user.is_student_user:
            allowed_student_perms = ['is_own_profile', 'can_view_student_timetable', 'student_attendance', 'can_view_my_leaves']
            return self.required_permission in allowed_student_perms or not self.required_permission

        if not self.required_permission:
            return True
        return self.request.user.has_role_permission(self.required_permission)

    def handle_no_permission(self):
        messages.error(self.request, "Access Denied: You do not have permission to access this management registry.")
        return HttpResponseRedirect(reverse_lazy('dashboard'))

class ERPListView(ERPBaseMixin, ListView):
    template_name = 'generic/list.html'
    list_fields = [] # List of field names to display

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        # 1. Superusers & Global Admins bypass filtering
        if user.is_superuser or not user.has_role_permission('can_view_dept_data'):
            return qs

        # 2. Contextual Filtering for HOD/Teachers (Dept Isolation)
        try:
            faculty = user.faculty_profile
            dept = faculty.department
            if dept:
                # 1. Direct department link (Student, FacultyProfile, etc.)
                if hasattr(self.model, 'department'):
                    return qs.filter(department=dept)
                # 2. Subject link (Subject -> Branch -> Program -> Dept)
                elif self.model.__name__ == 'Subject':
                    return qs.filter(branch__program__dept=dept)
                # 3. User link (User -> Student/Faculty -> Dept)
                elif self.model.__name__ == 'User':
                    from apps.students.models import Student
                    from apps.faculty.models import FacultyProfile
                    return qs.filter(
                        models.Q(student_profile__department=dept) | 
                        models.Q(faculty_profile__department=dept)
                    ).distinct()
        except Exception as e:
            print(f"Filtering Error: {e}")
            pass

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Extract headers from model metadata if not provided
        model = self.model
        if not self.list_fields:
            self.list_fields = [f.name for f in model._meta.fields if not f.is_relation]
            
        headers = []
        for field_name in self.list_fields:
            try:
                headers.append(model._meta.get_field(field_name).verbose_name.title())
            except:
                headers.append(field_name.title())
        
        context['headers'] = headers
        context['field_names'] = self.list_fields
        # Permission Flags
        user = self.request.user
        context['can_add'] = user.is_superuser or user.has_role_permission(f"can_manage_{self.model._meta.model_name}s") or user.has_role_permission("can_manage_academic_registry")
        context['can_edit'] = context['can_add']
        
        # Support for custom create URL (like the Student Admission Wizard)
        context['create_url'] = getattr(self, 'create_url', 'create/')
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        ids = request.POST.getlist('ids')
        
        if not ids:
            return HttpResponseRedirect(request.path)
            
        if action == 'delete':
            return self.handle_bulk_delete(ids)
        elif action == 'export':
            return self.handle_bulk_export(ids)
            
        return HttpResponseRedirect(request.path)

    def handle_bulk_delete(self, ids):
        if not self.request.user.is_staff:
            return HttpResponse(status=403)
        self.model.objects.filter(pk__in=ids).delete()
        return HttpResponseRedirect(self.request.path)

    def handle_bulk_export(self, ids):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{self.module_name}_export.csv"'

        writer = csv.writer(response)

        # Build headers directly (do NOT call get_context_data here to avoid object_list error)
        model = self.model
        fields = self.list_fields or [f.name for f in model._meta.fields if not f.is_relation]
        headers = []
        for field_name in fields:
            try:
                headers.append(model._meta.get_field(field_name).verbose_name.title())
            except:
                headers.append(field_name.title())
        writer.writerow(headers)

        # Data rows
        queryset = self.model.objects.filter(pk__in=ids)
        for obj in queryset:
            row = []
            for field in fields:
                val = getattr(obj, field, '-')
                if hasattr(val, 'get_username'):
                    row.append(val.get_username())
                else:
                    row.append(str(val))
            writer.writerow(row)

        return response

class ERPCreateView(ERPBaseMixin, CreateView):
    template_name = 'generic/form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action_title'] = f"Add New {self.module_name}"
        context['is_update'] = False
        return context

class ERPUpdateView(ERPBaseMixin, UpdateView):
    template_name = 'generic/form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action_title'] = f"Edit {self.module_name}"
        context['is_update'] = True
        context['object_id'] = self.object.pk
        return context

class ERPDetailView(ERPBaseMixin, DetailView):
    template_name = 'generic/detail.html'
    detail_fields = []

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user

        # Superusers and Global Admins bypass
        if user.is_superuser or not user.has_role_permission('can_view_dept_data'):
            return obj

        # Departmental Isolation Check
        try:
            faculty = user.faculty_profile
            dept = faculty.department
            if dept:
                # 1. Check if object has direct department link
                if hasattr(obj, 'department'):
                    if obj.department != dept:
                        from django.core.exceptions import PermissionDenied
                        raise PermissionDenied("You do not have permission to view records outside your department.")
                # 2. Check if object is User (check THEIR profile)
                elif isinstance(obj, user.__class__):
                    # Check if student/faculty belongs to dept
                    is_in_dept = False
                    if hasattr(obj, 'student_profile') and obj.student_profile.department == dept:
                        is_in_dept = True
                    elif hasattr(obj, 'faculty_profile') and obj.faculty_profile.department == dept:
                        is_in_dept = True
                    
                    if not is_in_dept:
                        from django.core.exceptions import PermissionDenied
                        raise PermissionDenied("You do not have permission to view records outside your department.")
        except PermissionDenied as e:
            raise e
        except:
            pass
            
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model = self.model
        obj = self.object
        
        # 1. Initialize Groups
        groups = {
            'personal': {'label': 'Personal Information', 'icon': 'fa-user-circle', 'fields': []},
            'contact': {'label': 'Communication Details', 'icon': 'fa-address-book', 'fields': []},
            'academic': {'label': 'Academic Progress', 'icon': 'fa-graduation-cap', 'fields': []},
            'professional': {'label': 'Professional Details', 'icon': 'fa-briefcase', 'fields': []},
            'system': {'label': 'System Metadata', 'icon': 'fa-database', 'fields': []},
        }
        
        # 2. Heuristic Categorization Helper
        def categorize_field(f_name, f_label, f_value):
            data = {'name': f_name, 'label': f_label, 'value': f_value}
            fname = f_name.lower()
            if any(x in fname for x in ['email', 'phone', 'mobile', 'address', 'city', 'state', 'pincode']):
                groups['contact']['fields'].append(data)
            elif any(x in fname for x in ['roll', 'cgpa', 'attendance', 'course', 'batch', 'sem', 'branch', 'dept', 'program', 'admission']):
                groups['academic']['fields'].append(data)
            elif any(x in fname for x in ['designation', 'salary', 'experience', 'id_counter', 'joining_date', 'employee_id', 'qualification']):
                groups['professional']['fields'].append(data)
            elif any(x in fname for x in ['is_active', 'date_', 'last_login', 'password', 'user_permissions', 'groups', 'is_staff', 'is_superuser']):
                if f_name not in ['password', 'user_permissions', 'groups']: 
                    groups['system']['fields'].append(data)
            else:
                groups['personal']['fields'].append(data)

        # 3. Process Primary Model Fields
        target_fields = self.detail_fields or [f.name for f in model._meta.fields]
        for f in target_fields:
            try:
                field_obj = model._meta.get_field(f)
                categorize_field(f, field_obj.verbose_name.title(), getattr(obj, f))
            except: continue

        # 4. Process Related Profiles (FOR USERS)
        # If we are looking at a User, automatically pull in their Profile data
        profile_obj = None
        if hasattr(obj, 'student_profile'): 
            profile_obj = obj.student_profile
        elif hasattr(obj, 'faculty_profile'): 
            profile_obj = obj.faculty_profile
        elif hasattr(obj, 'staff_profile'): 
            profile_obj = obj.staff_profile
        
        if profile_obj:
            context['profile_object'] = profile_obj
            for f in profile_obj._meta.fields:
                if f.name in ['id', 'user']: continue # Skip generic links
                categorize_field(f.name, f.verbose_name.title(), getattr(profile_obj, f.name))

        # 5. Final Context Prep
        context['field_groups'] = {k: v for k, v in groups.items() if v['fields']}
        context['field_names'] = target_fields # Restore for templates relying on it
        context['module_name_singular'] = self.module_name.rstrip('s')
        
        # Mode detection for template
        context['is_admin_mode'] = self.request.user.role != 'STUDENT'
        context['is_own_profile'] = self.request.user == (obj if hasattr(obj, 'role') else getattr(obj, 'user', None))
        
        return context
