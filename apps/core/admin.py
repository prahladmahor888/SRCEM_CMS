from django.contrib import admin
from .models import (
    College, CollegeSettings, Department, Program, Branch, Subject, SubjectTopic, StudyMaterial, PublicNotice,
    HeroSlide, CollegeEvent, HomeProgram, GalleryItem, Recruiter, CollegeStat, AboutSectionConfig,
    PlacementConfig, PlacementAchiever, PlacementTrainingFeature, PlacementProcessStep, ExamSchedule
)

@admin.register(PublicNotice)
class PublicNoticeAdmin(admin.ModelAdmin):
    list_display = ('title', 'notice_type', 'is_popup', 'is_active', 'created_at')
    list_filter = ('notice_type', 'is_popup', 'is_active')
    search_fields = ('title', 'content')

@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'subtitle')

@admin.register(CollegeEvent)
class CollegeEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_date', 'venue', 'is_active')
    list_filter = ('is_active', 'event_date')
    search_fields = ('title', 'venue')

@admin.register(HomeProgram)
class HomeProgramAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'description')

@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'order', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('title',)

@admin.register(Recruiter)
class RecruiterAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(CollegeStat)
class CollegeStatAdmin(admin.ModelAdmin):
    list_display = ('label', 'value', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('label', 'value')

@admin.register(AboutSectionConfig)
class AboutSectionConfigAdmin(admin.ModelAdmin):
    list_display = ('title', 'director_name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'director_name', 'director_message')

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('subject_name', 'subject_code', 'branch', 'semester', 'subject_type')
    list_filter = ('branch', 'semester', 'subject_type')
    search_fields = ('subject_name', 'subject_code')

@admin.register(SubjectTopic)
class SubjectTopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'unit_number', 'order')
    list_filter = ('subject', 'unit_number')
    search_fields = ('title', 'subject__subject_name')

@admin.register(StudyMaterial)
class StudyMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'material_type', 'faculty', 'uploaded_at')
    list_filter = ('material_type', 'subject', 'uploaded_at')
    search_fields = ('title', 'subject__subject_name')

@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ('name', 'college_code', 'website', 'created_at')
    search_fields = ('name', 'college_code')

@admin.register(CollegeSettings)
class CollegeSettingsAdmin(admin.ModelAdmin):
    list_display = ('college', 'setting_key', 'setting_value', 'updated_at')
    list_filter = ('college', 'setting_key')

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('dept_name', 'dept_code', 'college')
    list_filter = ('college',)
    search_fields = ('dept_name', 'dept_code')

@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('program_name', 'program_code', 'dept')
    list_filter = ('dept',)
    search_fields = ('program_name', 'program_code')

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('branch_name', 'branch_code', 'program', 'duration_years')
    list_filter = ('program',)
    search_fields = ('branch_name', 'branch_code')


@admin.register(PlacementConfig)
class PlacementConfigAdmin(admin.ModelAdmin):
    list_display = ('banner_title', 'highest_package', 'average_package', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('banner_title', 'banner_subtitle')


@admin.register(PlacementAchiever)
class PlacementAchieverAdmin(admin.ModelAdmin):
    list_display = ('student_name', 'company_name', 'package', 'branch', 'placed_year', 'is_highest', 'is_active')
    list_filter = ('placed_year', 'is_highest', 'is_active', 'company_name')
    search_fields = ('student_name', 'company_name', 'branch')


@admin.register(PlacementTrainingFeature)
class PlacementTrainingFeatureAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title',)


@admin.register(PlacementProcessStep)
class PlacementProcessStepAdmin(admin.ModelAdmin):
    list_display = ('step_number', 'title', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'description')


@admin.register(ExamSchedule)
class ExamScheduleAdmin(admin.ModelAdmin):
    list_display = ('subject', 'date', 'start_time', 'end_time', 'venue', 'exam_type')
    list_filter = ('exam_type', 'date', 'venue')
    search_fields = ('subject__subject_name', 'venue')

