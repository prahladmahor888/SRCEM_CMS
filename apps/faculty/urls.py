from django.urls import path
from . import views

urlpatterns = [
    # Faculty Profiles
    path('faculty-list/', views.FacultyProfileListView.as_view(), name='faculty_list'),
    path('faculty-list/admission/', views.FacultyAdmissionWizardView.as_view(), name='faculty_admission'),
    path('faculty-list/create/', views.FacultyProfileCreateView.as_view(), name='faculty_create'),
    path('faculty-list/<int:pk>/', views.FacultyProfileDetailView.as_view(), name='faculty_detail'),
    path('faculty-list/<int:pk>/edit/', views.FacultyProfileUpdateView.as_view(), name='faculty_update'),

    # Syllabus Progress
    path('syllabus-progress/', views.SyllabusProgressListView.as_view(), name='syllabus_progress_list'),
    path('my-syllabus-progress/', views.MySyllabusProgressListView.as_view(), name='my_syllabus_progress'),
    path('syllabus-progress/<int:pk>/update/', views.SyllabusProgressUpdateView.as_view(), name='syllabus_progress_update'),
    
    # Subject Topics
    path('subject-topics/create/', views.SubjectTopicCreateView.as_view(), name='subject_topic_create'),

    # Subject Allotment
    path('subject-allotments/', views.SubjectAllotmentListView.as_view(), name='subject_allotment_list'),
    path('subject-allotments/create/', views.SubjectAllotmentCreateView.as_view(), name='subject_allotment_create'),
    path('subject-allotments/<int:pk>/', views.SubjectAllotmentDetailView.as_view(), name='subject_allotment_detail'),
    path('subject-allotments/<int:pk>/edit/', views.SubjectAllotmentUpdateView.as_view(), name='subject_allotment_update'),
    path('subject-allotments/<int:pk>/delete/', views.SubjectAllotmentDeleteView.as_view(), name='subject_allotment_delete'),
    path('subject-allotments/filter-subjects/', views.GetFilteredSubjectsView.as_view(), name='filter_subjects'),
    
    # Timetables
    path('dept-timetable/', views.DepartmentTimetableView.as_view(), name='dept_timetable'),
    path('timetable/session/add/', views.SubjectScheduleCreateView.as_view(), name='session_create'),
    path('timetable/session/<int:pk>/edit/', views.SubjectScheduleUpdateView.as_view(), name='session_update'),
    path('timetable/session/<int:pk>/delete/', views.SubjectScheduleDeleteView.as_view(), name='session_delete'),
    path('timetable/session/filter-allotments/', views.GetFilteredAllotmentsView.as_view(), name='filter_allotments'),
    path('my-timetable/', views.MyTimetableView.as_view(), name='my_timetable'),

    # Professional Hub
    path('my-publications/', views.MyResearchPublicationListView.as_view(), name='my_publications'),
    path('my-documents/', views.MyFacultyDocumentListView.as_view(), name='my_documents'),
    
    # Attendance
    path('mark-attendance/', views.MarkAttendanceView.as_view(), name='mark_attendance'),

    # Leave Management
    path('leave-approvals/', views.StudentLeaveApprovalListView.as_view(), name='leave_approval_list'),
    path('leave-approvals/<int:pk>/<str:action>/', views.StudentLeaveActionView.as_view(), name='leave_action'),
    path('my-leaves/', views.FacultyMyLeaveListView.as_view(), name='faculty_my_leaves'),
    path('enter-marks/', views.EnterMarksView.as_view(), name='enter_marks'),
]