from django.contrib import admin
from .models import (
    Student, Guardian, Document, AdmissionEnquiry, MidTermMark,
    CommunicationTemplate, CommunicationLog, StudentLeave, AssignmentSubmission,
    OnlineAdmissionRegistration, Project, ProjectMember, ProjectWeeklyLog, ProjectDeliverable
)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('roll_number', 'user', 'branch', 'enrollment_number', 'semester', 'status')
    search_fields = ('roll_number', 'enrollment_number', 'user__login_id', 'user__first_name', 'user__last_name')
    list_filter = ('branch', 'semester', 'status', 'batch_year')

@admin.register(AdmissionEnquiry)
class AdmissionEnquiryAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'course_interested', 'status', 'created_at')
    list_filter = ('status', 'course_interested', 'created_at')
    search_fields = ('name', 'phone', 'email')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('document_type', 'student', 'verified', 'uploaded_at')
    list_filter = ('document_type', 'verified', 'uploaded_at')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'student__enrollment_number')

@admin.register(MidTermMark)
class MidTermMarkAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'mid_term_type', 'obtained_marks', 'max_marks', 'remarks')
    list_filter = ('mid_term_type', 'subject')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'student__roll_number')


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ('name', 'student', 'relation', 'phone', 'is_primary')
    list_filter = ('relation', 'is_primary')
    search_fields = ('name', 'student__user__first_name', 'student__user__last_name')


@admin.register(CommunicationTemplate)
class CommunicationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'subject', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('name', 'subject', 'body')


@admin.register(CommunicationLog)
class CommunicationLogAdmin(admin.ModelAdmin):
    list_display = ('recipient_name', 'recipient_contact', 'channel', 'status', 'sent_at')
    list_filter = ('channel', 'status', 'sent_at')
    search_fields = ('recipient_name', 'recipient_contact', 'subject', 'body')


@admin.register(StudentLeave)
class StudentLeaveAdmin(admin.ModelAdmin):
    list_display = ('student', 'leave_type', 'start_date', 'end_date', 'status')
    list_filter = ('leave_type', 'status', 'start_date')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'reason')


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'assignment', 'submitted_at', 'status', 'points_obtained')
    list_filter = ('status', 'submitted_at')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'assignment__title')


@admin.register(OnlineAdmissionRegistration)
class OnlineAdmissionRegistrationAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone', 'applied_course', 'status', 'created_at')
    list_filter = ('status', 'entry_type', 'program_category', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'phone')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'mentor', 'branch', 'semester', 'progress')
    list_filter = ('semester', 'branch', 'progress')
    search_fields = ('title', 'description', 'mentor__user__first_name')


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ('project', 'student', 'role')
    list_filter = ('role',)
    search_fields = ('project__title', 'student__user__first_name', 'student__user__last_name')


@admin.register(ProjectWeeklyLog)
class ProjectWeeklyLogAdmin(admin.ModelAdmin):
    list_display = ('project', 'student', 'week_title', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('project__title', 'student__user__first_name', 'week_title')


@admin.register(ProjectDeliverable)
class ProjectDeliverableAdmin(admin.ModelAdmin):
    list_display = ('project', 'student', 'title', 'category', 'status', 'uploaded_at')
    list_filter = ('category', 'status', 'uploaded_at')
    search_fields = ('project__title', 'student__user__first_name', 'title')
