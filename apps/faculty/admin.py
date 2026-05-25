from django.contrib import admin
from .models import (
    FacultyProfile, FacultyDocument, SubjectAllotment, SyllabusCoverage, ResearchPublication,
    SubjectSchedule, StudentAttendance, Assignment, FacultyLeaveBalance, FacultyLeave
)

@admin.register(FacultyProfile)
class FacultyProfileAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'user', 'department', 'designation')
    search_fields = ('employee_id', 'user__login_id', 'user__first_name')
    list_filter = ('department', 'designation', 'joining_date')

@admin.register(SubjectAllotment)
class SubjectAllotmentAdmin(admin.ModelAdmin):
    list_display = ('subject', 'faculty', 'semester', 'session')
    list_filter = ('session', 'subject__semester', 'faculty__department')
    search_fields = ('subject__subject_name', 'faculty__user__first_name')

@admin.register(SyllabusCoverage)
class SyllabusCoverageAdmin(admin.ModelAdmin):
    list_display = ('allotment', 'percentage', 'last_updated')
    list_editable = ('percentage',)

@admin.register(ResearchPublication)
class ResearchPublicationAdmin(admin.ModelAdmin):
    list_display = ('title', 'faculty', 'pub_type', 'publication_date')
    list_filter = ('pub_type', 'faculty__department')


@admin.register(FacultyDocument)
class FacultyDocumentAdmin(admin.ModelAdmin):
    list_display = ('document_type', 'faculty', 'verified', 'uploaded_at')
    list_filter = ('document_type', 'verified', 'uploaded_at')
    search_fields = ('faculty__user__first_name', 'faculty__user__last_name', 'faculty__employee_id')


@admin.register(SubjectSchedule)
class SubjectScheduleAdmin(admin.ModelAdmin):
    list_display = ('allotment', 'day', 'session_type', 'start_time', 'end_time', 'room_number')
    list_filter = ('day', 'session_type', 'room_number')
    search_fields = ('allotment__subject__subject_name', 'allotment__faculty__user__first_name')


@admin.register(StudentAttendance)
class StudentAttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'allotment', 'date', 'section', 'session_type', 'status')
    list_filter = ('status', 'session_type', 'section', 'date')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'student__roll_number')


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'faculty', 'due_date', 'is_active')
    list_filter = ('is_active', 'due_date', 'subject')
    search_fields = ('title', 'description', 'faculty__user__first_name')


@admin.register(FacultyLeaveBalance)
class FacultyLeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ('faculty', 'year', 'cl_total', 'cl_used', 'sl_total', 'sl_used', 'al_total', 'al_used')
    list_filter = ('year',)
    search_fields = ('faculty__user__first_name', 'faculty__employee_id')


@admin.register(FacultyLeave)
class FacultyLeaveAdmin(admin.ModelAdmin):
    list_display = ('faculty', 'leave_type', 'start_date', 'end_date', 'status')
    list_filter = ('leave_type', 'status', 'start_date')
    search_fields = ('faculty__user__first_name', 'reason')
