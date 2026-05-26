from django.urls import path
from . import views
from apps.accounts import views as account_views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin-dashboard/', views.admin, name='admin_dashboard'),
    path('student/', views.student, name='student_dashboard'),
    path('teacher/', views.teacher, name='teacher_dashboard'),
    path('profile/', account_views.profile_view, name='profile'),
    
    # User Management
    path('users/', account_views.UserListView.as_view(), name='user_list'),
    path('users/create/', account_views.UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/', account_views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/edit/', account_views.UserUpdateView.as_view(), name='user_update'),
    

    
    # Staff Profiles
    path('staff-list/', views.StaffProfileListView.as_view(), name='staff_list'),
    path('staff-list/create/', views.StaffProfileCreateView.as_view(), name='staff_create'),
    path('staff-list/<int:pk>/', views.StaffProfileDetailView.as_view(), name='staff_detail'),
    path('staff-list/<int:pk>/edit/', views.StaffProfileUpdateView.as_view(), name='staff_edit'), # Using edit suffix for consistency if needed
   
    # ID Counters
    path('id-counters/', views.IDCounterListView.as_view(), name='id_counter_list'),
    path('id-counters/create/', views.IDCounterCreateView.as_view(), name='id_counter_create'),
    path('id-counters/<int:pk>/', views.IDCounterDetailView.as_view(), name='id_counter_detail'),
    path('id-counters/<int:pk>/edit/', views.IDCounterUpdateView.as_view(), name='id_counter_edit'),

    # 🏛️ ACADEMIC HIERARCHY
    path('colleges/', views.CollegeListView.as_view(), name='college_list'),
    path('colleges/create/', views.CollegeCreateView.as_view(), name='college_create'),
    path('colleges/<int:pk>/', views.CollegeDetailView.as_view(), name='college_detail'),
    path('colleges/<int:pk>/edit/', views.CollegeUpdateView.as_view(), name='college_update'),

    path('departments/', views.DepartmentListView.as_view(), name='department_list'),
    path('departments/create/', views.DepartmentCreateView.as_view(), name='department_create'),
    path('departments/<int:pk>/', views.DepartmentDetailView.as_view(), name='department_detail'),
    path('departments/<int:pk>/edit/', views.DepartmentUpdateView.as_view(), name='department_update'),

    path('programs/', views.ProgramListView.as_view(), name='program_list'),
    path('programs/create/', views.ProgramCreateView.as_view(), name='program_create'),
    path('programs/<int:pk>/', views.ProgramDetailView.as_view(), name='program_detail'),
    path('programs/<int:pk>/edit/', views.ProgramUpdateView.as_view(), name='program_update'),

    path('branches/', views.BranchListView.as_view(), name='branch_list'),
    path('branches/create/', views.BranchCreateView.as_view(), name='branch_create'),
    path('branches/<int:pk>/', views.BranchDetailView.as_view(), name='branch_detail'),
    path('branches/<int:pk>/edit/', views.BranchUpdateView.as_view(), name='branch_update'),
    
    # Subjects
    path('subjects/', views.SubjectListView.as_view(), name='subject_list'),
    path('subjects/create/', views.SubjectCreateView.as_view(), name='subject_create'),
    path('subjects/<int:pk>/', views.SubjectDetailView.as_view(), name='subject_detail'),
    path('subjects/<int:pk>/edit/', views.SubjectUpdateView.as_view(), name='subject_update'),
    path('subjects/<int:pk>/delete/', views.SubjectDeleteView.as_view(), name='subject_delete'),

    path('institutional-settings/', views.CollegeSettingsListView.as_view(), name='college_settings_list'),
    path('institutional-settings/create/', views.CollegeSettingsCreateView.as_view(), name='college_settings_create'),
    path('institutional-settings/<int:pk>/', views.CollegeSettingsDetailView.as_view(), name='college_settings_detail'),
    path('institutional-settings/<int:pk>/edit/', views.CollegeSettingsUpdateView.as_view(), name='college_settings_edit'),

    # 🛡️ SECURITY & RBAC
    path('user-roles/', account_views.RoleListView.as_view(), name='role_list'),
    path('user-roles/create/', account_views.RoleCreateView.as_view(), name='role_create'),
    path('user-roles/<int:pk>/', account_views.RoleDetailView.as_view(), name='role_detail'),
    path('user-roles/<int:pk>/edit/', account_views.RoleUpdateView.as_view(), name='role_edit'),

    path('system-permissions/', account_views.PermissionListView.as_view(), name='permission_list'),
    path('system-permissions/create/', account_views.PermissionCreateView.as_view(), name='permission_create'),
    path('system-permissions/<int:pk>/', account_views.PermissionDetailView.as_view(), name='permission_detail'),
    path('system-permissions/<int:pk>/edit/', account_views.PermissionUpdateView.as_view(), name='permission_edit'),

    path('user-groups/', account_views.GroupListView.as_view(), name='group_list'),
    path('user-groups/create/', account_views.GroupCreateView.as_view(), name='group_create'),
    path('user-groups/<int:pk>/', account_views.GroupDetailView.as_view(), name='group_detail'),
    path('user-groups/<int:pk>/edit/', account_views.GroupUpdateView.as_view(), name='group_edit'),

    # Security Monitoring
    path('security-logs/', account_views.SecurityLogListView.as_view(), name='security_log_list'),
    path('security-logs/<int:pk>/', account_views.SecurityLogDetailView.as_view(), name='security_log_detail'),


    # 📤 BULK DATA TOOLS
    path('bulk-import/', views.BulkImportView.as_view(), name='bulk_import'),
    path('toggle-bulk-porter/', views.toggle_bulk_porter, name='toggle_bulk_porter'),
    path('bulk-outreach/', views.BulkOutreachView.as_view(), name='bulk_outreach'),

    # 🌐 WEBSITE CMS
    # 1. Hero Slide URLs
    path('cms/hero-slides/', views.HeroSlideListView.as_view(), name='cms_heroslide_list'),
    path('cms/hero-slides/create/', views.HeroSlideCreateView.as_view(), name='cms_heroslide_create'),
    path('cms/hero-slides/<int:pk>/', views.HeroSlideDetailView.as_view(), name='cms_heroslide_detail'),
    path('cms/hero-slides/<int:pk>/edit/', views.HeroSlideUpdateView.as_view(), name='cms_heroslide_edit'),
    path('cms/hero-slides/<int:pk>/delete/', views.HeroSlideDeleteView.as_view(), name='cms_heroslide_delete'),

    # 2. Public Notice URLs
    path('cms/public-notices/', views.PublicNoticeListView.as_view(), name='cms_publicnotice_list'),
    path('cms/public-notices/create/', views.PublicNoticeCreateView.as_view(), name='cms_publicnotice_create'),
    path('cms/public-notices/<int:pk>/', views.PublicNoticeDetailView.as_view(), name='cms_publicnotice_detail'),
    path('cms/public-notices/<int:pk>/edit/', views.PublicNoticeUpdateView.as_view(), name='cms_publicnotice_edit'),
    path('cms/public-notices/<int:pk>/delete/', views.PublicNoticeDeleteView.as_view(), name='cms_publicnotice_delete'),

    # 3. College Event URLs
    path('cms/college-events/', views.CollegeEventListView.as_view(), name='cms_collegeevent_list'),
    path('cms/college-events/create/', views.CollegeEventCreateView.as_view(), name='cms_collegeevent_create'),
    path('cms/college-events/<int:pk>/', views.CollegeEventDetailView.as_view(), name='cms_collegeevent_detail'),
    path('cms/college-events/<int:pk>/edit/', views.CollegeEventUpdateView.as_view(), name='cms_collegeevent_edit'),
    path('cms/college-events/<int:pk>/delete/', views.CollegeEventDeleteView.as_view(), name='cms_collegeevent_delete'),

    # 4. Home Program URLs
    path('cms/home-programs/', views.HomeProgramListView.as_view(), name='cms_homeprogram_list'),
    path('cms/home-programs/create/', views.HomeProgramCreateView.as_view(), name='cms_homeprogram_create'),
    path('cms/home-programs/<int:pk>/', views.HomeProgramDetailView.as_view(), name='cms_homeprogram_detail'),
    path('cms/home-programs/<int:pk>/edit/', views.HomeProgramUpdateView.as_view(), name='cms_homeprogram_edit'),
    path('cms/home-programs/<int:pk>/delete/', views.HomeProgramDeleteView.as_view(), name='cms_homeprogram_delete'),

    # 5. Campus Gallery URLs
    path('cms/gallery-items/', views.GalleryItemListView.as_view(), name='cms_galleryitem_list'),
    path('cms/gallery-items/create/', views.GalleryItemCreateView.as_view(), name='cms_galleryitem_create'),
    path('cms/gallery-items/<int:pk>/', views.GalleryItemDetailView.as_view(), name='cms_galleryitem_detail'),
    path('cms/gallery-items/<int:pk>/edit/', views.GalleryItemUpdateView.as_view(), name='cms_galleryitem_edit'),
    path('cms/gallery-items/<int:pk>/delete/', views.GalleryItemDeleteView.as_view(), name='cms_galleryitem_delete'),

    # 6. Recruiter URLs
    path('cms/recruiters/', views.RecruiterListView.as_view(), name='cms_recruiter_list'),
    path('cms/recruiters/create/', views.RecruiterCreateView.as_view(), name='cms_recruiter_create'),
    path('cms/recruiters/<int:pk>/', views.RecruiterDetailView.as_view(), name='cms_recruiter_detail'),
    path('cms/recruiters/<int:pk>/edit/', views.RecruiterUpdateView.as_view(), name='cms_recruiter_edit'),
    path('cms/recruiters/<int:pk>/delete/', views.RecruiterDeleteView.as_view(), name='cms_recruiter_delete'),

    # 7. College Stat URLs
    path('cms/college-stats/', views.CollegeStatListView.as_view(), name='cms_collegestat_list'),
    path('cms/college-stats/create/', views.CollegeStatCreateView.as_view(), name='cms_collegestat_create'),
    path('cms/college-stats/<int:pk>/', views.CollegeStatDetailView.as_view(), name='cms_collegestat_detail'),
    path('cms/college-stats/<int:pk>/edit/', views.CollegeStatUpdateView.as_view(), name='cms_collegestat_edit'),
    path('cms/college-stats/<int:pk>/delete/', views.CollegeStatDeleteView.as_view(), name='cms_collegestat_delete'),

    # 8. About Section Config URLs
    path('cms/about-configs/', views.AboutSectionConfigListView.as_view(), name='cms_aboutsectionconfig_list'),
    path('cms/about-configs/create/', views.AboutSectionConfigCreateView.as_view(), name='cms_aboutsectionconfig_create'),
    path('cms/about-configs/<int:pk>/', views.AboutSectionConfigDetailView.as_view(), name='cms_aboutsectionconfig_detail'),
    path('cms/about-configs/<int:pk>/edit/', views.AboutSectionConfigUpdateView.as_view(), name='cms_aboutsectionconfig_edit'),
    path('cms/about-configs/<int:pk>/delete/', views.AboutSectionConfigDeleteView.as_view(), name='cms_aboutsectionconfig_delete'),

    # 9. Placement Config URLs
    path('cms/placement-configs/', views.PlacementConfigListView.as_view(), name='cms_placementconfig_list'),
    path('cms/placement-configs/create/', views.PlacementConfigCreateView.as_view(), name='cms_placementconfig_create'),
    path('cms/placement-configs/<int:pk>/', views.PlacementConfigDetailView.as_view(), name='cms_placementconfig_detail'),
    path('cms/placement-configs/<int:pk>/edit/', views.PlacementConfigUpdateView.as_view(), name='cms_placementconfig_edit'),
    path('cms/placement-configs/<int:pk>/delete/', views.PlacementConfigDeleteView.as_view(), name='cms_placementconfig_delete'),

    # 10. Placement Achiever URLs
    path('cms/placement-achievers/', views.PlacementAchieverListView.as_view(), name='cms_placementachiever_list'),
    path('cms/placement-achievers/create/', views.PlacementAchieverCreateView.as_view(), name='cms_placementachiever_create'),
    path('cms/placement-achievers/<int:pk>/', views.PlacementAchieverDetailView.as_view(), name='cms_placementachiever_detail'),
    path('cms/placement-achievers/<int:pk>/edit/', views.PlacementAchieverUpdateView.as_view(), name='cms_placementachiever_edit'),
    path('cms/placement-achievers/<int:pk>/delete/', views.PlacementAchieverDeleteView.as_view(), name='cms_placementachiever_delete'),

    # 11. Placement Training Feature URLs
    path('cms/placement-features/', views.PlacementTrainingFeatureListView.as_view(), name='cms_placementtrainingfeature_list'),
    path('cms/placement-features/create/', views.PlacementTrainingFeatureCreateView.as_view(), name='cms_placementtrainingfeature_create'),
    path('cms/placement-features/<int:pk>/', views.PlacementTrainingFeatureDetailView.as_view(), name='cms_placementtrainingfeature_detail'),
    path('cms/placement-features/<int:pk>/edit/', views.PlacementTrainingFeatureUpdateView.as_view(), name='cms_placementtrainingfeature_edit'),
    path('cms/placement-features/<int:pk>/delete/', views.PlacementTrainingFeatureDeleteView.as_view(), name='cms_placementtrainingfeature_delete'),

    # 12. Placement Process Step URLs
    path('cms/placement-steps/', views.PlacementProcessStepListView.as_view(), name='cms_placementprocessstep_list'),
    path('cms/placement-steps/create/', views.PlacementProcessStepCreateView.as_view(), name='cms_placementprocessstep_create'),
    path('cms/placement-steps/<int:pk>/', views.PlacementProcessStepDetailView.as_view(), name='cms_placementprocessstep_detail'),
    path('cms/placement-steps/<int:pk>/edit/', views.PlacementProcessStepUpdateView.as_view(), name='cms_placementprocessstep_edit'),
    path('cms/placement-steps/<int:pk>/delete/', views.PlacementProcessStepDeleteView.as_view(), name='cms_placementprocessstep_delete'),

    # 📦 DYNAMIC GENERIC REGISTRY
    path('generic-registry/<str:model_name>/', views.GenericModelListView.as_view(), name='generic_model_list'),
    path('generic-registry/<str:model_name>/create/', views.GenericModelCreateView.as_view(), name='generic_model_create'),
    path('generic-registry/<str:model_name>/<int:pk>/', views.GenericModelDetailView.as_view(), name='generic_model_detail'),
    path('generic-registry/<str:model_name>/<int:pk>/edit/', views.GenericModelUpdateView.as_view(), name='generic_model_update'),
    path('generic-registry/<str:model_name>/<int:pk>/delete/', views.GenericModelDeleteView.as_view(), name='generic_model_delete'),
    
    # Financial Exports for Accountant
    path('download-ledger-csv/', views.download_ledger_csv, name='download_ledger_csv'),
    path('daily-summary-report/', views.daily_summary_report, name='daily_summary_report'),
]