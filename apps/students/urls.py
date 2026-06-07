from django.urls import path
from . import views, api_views

urlpatterns = [
    # Public forms
    path('apply-now/', views.PublicApplyNowView.as_view(), name='apply_now'),

    # Student Profiles
    path('students-list/', views.StudentListView.as_view(), name='student_list'),
    path('students-list/create/', views.StudentCreateView.as_view(), name='student_create'),
    path('students-list/admission-wizard/', views.StudentAdmissionWizardView.as_view(), name='student_admission_wizard'),
    path('students-list/<int:pk>/', views.StudentDetailView.as_view(), name='student_detail'),
    path('students-list/<int:pk>/edit/', views.StudentUpdateView.as_view(), name='student_update'),

    # Student Self-Service
    path('curriculum-progress/', views.MyCurriculumProgressListView.as_view(), name='student_curriculum'),
    path('my-attendance/', views.StudentAttendanceOverviewView.as_view(), name='student_attendance'),
    path('student-timetable/', views.StudentTimetableView.as_view(), name='student_timetable'),
    path('study-materials/', views.StudentStudyMaterialListView.as_view(), name='student_study_materials'),
    path('assignment-hub/', views.StudentAssignmentListView.as_view(), name='student_assignment_hub'),
    path('assignment-submit/<int:pk>/', views.AssignmentSubmitView.as_view(), name='submit_assignment'),
    path('assignment-submit-form/<int:pk>/', views.AssignmentSubmitFormView.as_view(), name='assignment_submit_form'),
    path('student/my-leaves/', views.StudentMyLeaveListView.as_view(), name='student_my_leaves'),
    path('student/project/', views.StudentProjectConsoleView.as_view(), name='student_project_console'),
    path('student/project/weekly-log/', views.SubmitWeeklyLogView.as_view(), name='submit_weekly_log'),
    path('student/project/weekly-log-form/', views.ProjectWeeklyLogFormView.as_view(), name='weekly_log_form'),
    path('student/project/upload-deliverable/', views.UploadDeliverableView.as_view(), name='upload_project_deliverable'),
    path('student/project/upload-deliverable-form/', views.ProjectDeliverableFormView.as_view(), name='upload_deliverable_form'),
    path('my-marks/', views.StudentMarksView.as_view(), name='student_marks'),



    # Admin APIs
    path('api/admin/bulk-admission/', api_views.BulkAdmissionAPIView.as_view(), name='api_bulk_admission'),

    # Apply Now Requests (Admin/Staff)
    path('admission-requests/', views.OnlineAdmissionRegistrationListView.as_view(), name='admission_requests_list'),
    path('admission-requests/merit-list/', views.AdmissionMeritListView.as_view(), name='admission_merit_list'),
    path('admission-requests/<int:pk>/', views.OnlineAdmissionRegistrationDetailView.as_view(), name='admission_requests_detail'),
]