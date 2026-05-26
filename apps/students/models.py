from django.db import models
from django.conf import settings
from apps.core.models import Department, Program, Branch

class Student(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('graduated', 'Graduated'),
    ]
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'),
        ('O+', 'O+'), ('O-', 'O-'), ('AB+', 'AB+'), ('AB-', 'AB-'),
    ]
    CATEGORY_CHOICES = [
        ('General', 'General'),
        ('OBC', 'OBC'),
        ('SC', 'SC'),
        ('ST', 'ST'),
        ('EWS', 'EWS'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')

    # Academic info
    roll_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    enrollment_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    program = models.ForeignKey(Program, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    
    semester = models.IntegerField(default=1)
    section = models.CharField(max_length=10, default='A', null=True, blank=True)
    admission_date = models.DateField(null=True, blank=True)
    batch_year = models.IntegerField(null=True, blank=True) # YEAR type in MySQL
    FEE_CATEGORY_CHOICES = [
        ('fees_base', 'Regular Fee Based'),
        ('scholarship_base', 'Scholarship Based'),
        ('tfw', 'Tuition Fee Waiver (TFW)'),
        ('management_quota', 'Management Quota'),
    ]

    cgpa = models.DecimalField(max_digits=4, decimal_places=2, default=0.00, null=True, blank=True)
    admission_semester_fee = models.DecimalField(max_digits=10, decimal_places=2, default=75000.00, help_text="Agreed semester fee package at admission")
    one_time_admission_fee = models.DecimalField(max_digits=10, decimal_places=2, default=5000.00, help_text="One-time charges at the time of admission")
    fee_category = models.CharField(max_length=50, choices=FEE_CATEGORY_CHOICES, default='fees_base', help_text="Fee base/scholarship base quota type")
    referred_by = models.CharField(max_length=150, null=True, blank=True, help_text="Who referenced the student admission")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Mentorship
    mentor = models.ForeignKey('faculty.FacultyProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='mentees')

    # Personal info
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUP_CHOICES, null=True, blank=True)
    phone_alt = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    nationality = models.CharField(max_length=50, null=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, null=True, blank=True)

    # Profile & Bio
    profile_photo = models.ImageField(upload_to='students/photos/', null=True, blank=True)
    bio = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'students'
        indexes = [
            models.Index(fields=['branch'], name='idx_student_branch'),
            models.Index(fields=['department'], name='idx_student_dept'),
            models.Index(fields=['program'], name='idx_student_program'),
        ]

    def save(self, *args, **kwargs):
        # Sync enrollment_number with user.enrollment_id if it exists
        if not self.enrollment_number and self.user and hasattr(self.user, 'enrollment_id'):
            self.enrollment_number = self.user.enrollment_id
        super().save(*args, **kwargs)

    @staticmethod
    def GET_BATCH_YEAR_CHOICES():
        """Returns a list of tuples for batch year selection (2020-2032)"""
        return [(y, str(y)) for y in range(2020, 2033)]

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.enrollment_number or self.roll_number})"

class Guardian(models.Model):
    RELATION_CHOICES = [
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('guardian', 'Guardian'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='guardians')
    name = models.CharField(max_length=100)
    relation = models.CharField(max_length=20, choices=RELATION_CHOICES)
    phone = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(max_length=100, null=True, blank=True)
    occupation = models.CharField(max_length=100, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'guardian'
        indexes = [
            models.Index(fields=['student'], name='idx_student_id'),
        ]

    def __str__(self):
        return f"{self.name} ({self.relation} of {self.student.user.get_full_name()})"

class Document(models.Model):
    DOCUMENT_TYPES = [
        ('10th Marksheet', '10th Marksheet'),
        ('12th Marksheet', '12th Marksheet'),
        ('Aadhar Card', 'Aadhar Card'),
        ('Caste Certificate (Jati)', 'Caste Certificate (Jati)'),
        ('Domicile Certificate (Mool Niwas)', 'Domicile Certificate (Mool Niwas)'),
        ('Transfer Certificate (TC)', 'Transfer Certificate (TC)'),
        ('Migration Certificate', 'Migration Certificate'),
        ('Income Certificate', 'Income Certificate'),
        ('Other Document', 'Other Document'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES) # e.g., '10th Marksheet'
    file_url = models.CharField(max_length=255, null=True, blank=True) # Manual URL if needed
    file = models.FileField(upload_to='students/documents/', null=True, blank=True) # Actual storage
    file_name = models.CharField(max_length=255, null=True, blank=True)
    file_size = models.IntegerField(null=True, blank=True) # In bytes
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    remarks = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'documents'
        constraints = [
            models.UniqueConstraint(fields=['student', 'document_type'], name='unique_student_document_type')
        ]
        indexes = [
            models.Index(fields=['student'], name='idx_doc_student_id'),
        ]

    def __str__(self):
        return f"{self.document_type} - {self.student.user.get_full_name()}"

class AdmissionEnquiry(models.Model):
    STATUS_CHOICES = [
        ('New', 'New'),
        ('Follow-up', 'Follow-up'),
        ('Verified', 'Verified'),
        ('Rejected', 'Rejected'),
        ('Converted', 'Converted'),
    ]
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    course_interested = models.ForeignKey(Program, on_delete=models.SET_NULL, null=True, blank=True)
    source = models.CharField(max_length=100, blank=True, null=True) # e.g., Website, Walk-in
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='New')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'admission_enquiry'
        verbose_name_plural = "Admission Enquiries"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.course_interested or 'General'}"

class CommunicationTemplate(models.Model):
    TEMPLATE_TYPES = [
        ('SMS', 'SMS'),
        ('Email', 'Email'),
        ('WhatsApp', 'WhatsApp'),
    ]
    name = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=10, choices=TEMPLATE_TYPES)
    subject = models.CharField(max_length=255, blank=True, null=True) # For Email
    body = models.TextField() # Supports {{name}}, {{course}} etc.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'communication_templates'

    def __str__(self):
        return f"{self.name} ({self.type})"

class CommunicationLog(models.Model):
    CHANNELS = [
        ('SMS', 'SMS'),
        ('Email', 'Email'),
        ('WhatsApp', 'WhatsApp'),
    ]
    STATUS_CHOICES = [
        ('Sent', 'Sent'),
        ('Failed', 'Failed'),
    ]
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    recipient_name = models.CharField(max_length=150)
    recipient_contact = models.CharField(max_length=100) # Phone or Email
    channel = models.CharField(max_length=10, choices=CHANNELS)
    subject = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Sent')
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'communication_logs'
        ordering = ['-sent_at']

    def __str__(self):
        return f"To: {self.recipient_name} via {self.channel} at {self.sent_at}"

class StudentLeave(models.Model):
    LEAVE_TYPES = [
        ('Sick Leave', 'Sick Leave'),
        ('Personal Event', 'Personal Event'),
        ('College Event', 'College Event'),
        ('Emergency', 'Emergency'),
        ('Other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='leaves')
    mentor = models.ForeignKey('faculty.FacultyProfile', on_delete=models.CASCADE, related_name='student_leaves')
    
    leave_type = models.CharField(max_length=50, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    attachment = models.FileField(upload_to='students/leaves/', null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    mentor_remarks = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'student_leaves'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.leave_type} ({self.status})"
    
    @property
    def duration_days(self):
        return (self.end_date - self.start_date).days + 1

class AssignmentSubmission(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
    ]
    assignment = models.ForeignKey('faculty.Assignment', on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='assignment_submissions')
    
    file = models.FileField(upload_to='assignments/submissions/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    points_obtained = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'student_assignment_submissions'
        unique_together = ('assignment', 'student')

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.assignment.title}"

class OnlineAdmissionRegistration(models.Model):
    # Personal Info
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    
    # Program Info
    entry_type = models.CharField(max_length=20)
    program_category = models.CharField(max_length=20)
    applied_course = models.ForeignKey(Program, on_delete=models.SET_NULL, null=True)
    branch = models.CharField(max_length=50)
    
    # Academic Info
    high_school_board = models.CharField(max_length=100)
    high_school_year = models.CharField(max_length=20)
    high_school_percentage = models.CharField(max_length=20)
    
    higher_secondary_board = models.CharField(max_length=100, blank=True, null=True)
    higher_secondary_year = models.CharField(max_length=20, blank=True, null=True)
    higher_secondary_percentage = models.CharField(max_length=20, blank=True, null=True)
    
    lateral_university = models.CharField(max_length=100, blank=True, null=True)
    lateral_year = models.CharField(max_length=20, blank=True, null=True)
    lateral_percentage = models.CharField(max_length=20, blank=True, null=True)
    
    # Documents
    photo = models.FileField(upload_to='admissions/photos/', null=True, blank=True)
    marksheet = models.FileField(upload_to='admissions/marksheets/', null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'online_admission_registrations'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.applied_course}"


class Project(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    synopsis = models.TextField(null=True, blank=True)
    
    # overall metrics
    progress = models.IntegerField(default=0)  # e.g., 75%
    milestones_completed = models.IntegerField(default=0)
    milestones_total = models.IntegerField(default=4)
    presentation_date = models.DateField(null=True, blank=True)
    github_url = models.URLField(null=True, blank=True)
    
    # connections
    mentor = models.ForeignKey('faculty.FacultyProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='mentored_projects')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    semester = models.IntegerField(default=6)
    
    # metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'student_projects'

    def __str__(self):
        return self.title

class ProjectMember(models.Model):
    ROLE_CHOICES = [
        ('Leader', 'Team Leader'),
        ('FullStack', 'Full Stack Developer'),
        ('Frontend', 'Frontend Developer'),
        ('Backend', 'Backend Developer'),
        ('Designer', 'UI/UX Designer'),
        ('ML', 'ML Developer'),
        ('Member', 'Team Member'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='members')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='projects')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='Member')
    
    class Meta:
        db_table = 'student_project_members'
        unique_together = ('project', 'student')

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.project.title} ({self.get_role_display()})"

class ProjectWeeklyLog(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='weekly_logs')
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    week_title = models.CharField(max_length=255)
    accomplishments = models.TextField()
    commit_tag = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'student_project_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.week_title} - {self.project.title}"

class ProjectDeliverable(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending Review'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    CATEGORY_CHOICES = [
        ('Synopsis', 'Synopsis Proposal'),
        ('SRS', 'SRS Specification Doc'),
        ('Code', 'Phase Code Archive'),
        ('Other', 'Other Deliverable'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='deliverables')
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Other')
    file = models.FileField(upload_to='projects/deliverables/')
    file_name = models.CharField(max_length=255, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    class Meta:
        db_table = 'student_project_deliverables'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} - {self.project.title}"

class MidTermMark(models.Model):
    MID_TERM_CHOICES = [
        ('midterm1', 'Mid-Term 1 (MST-1)'),
        ('midterm2', 'Mid-Term 2 (MST-2)'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='midterm_marks')
    subject = models.ForeignKey('core.Subject', on_delete=models.CASCADE, related_name='midterm_marks')
    mid_term_type = models.CharField(max_length=20, choices=MID_TERM_CHOICES, default='midterm1')
    obtained_marks = models.DecimalField(max_digits=5, decimal_places=2)
    max_marks = models.DecimalField(max_digits=5, decimal_places=2, default=30.00)
    remarks = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'student_midterm_marks'
        unique_together = ('student', 'subject', 'mid_term_type')

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.subject.subject_name} ({self.get_mid_term_type_display()}): {self.obtained_marks}/{self.max_marks}"
