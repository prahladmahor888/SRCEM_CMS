from django.db import models
from django.conf import settings
from apps.core.models import Department, Subject, SubjectTopic
from django.utils import timezone

class FacultyProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='faculty_profile')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, related_name='faculty_members', null=True, blank=True)
    employee_id = models.CharField(max_length=50, unique=True)
    designation = models.CharField(max_length=100, null=True, blank=True)
    qualification = models.CharField(max_length=255, null=True, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    
    class Meta:
        db_table = 'faculty_profile'
        indexes = [
            models.Index(fields=['department'], name='idx_faculty_dept'),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_id})"

class FacultyDocument(models.Model):
    DOCUMENT_TYPES = [
        ('Joining Letter', 'Joining Letter'),
        ('Resume', 'Resume'),
        ('Experience Certificate', 'Experience Certificate'),
        ('Qualification Proof', 'Qualification Proof'),
        ('Aadhar Card', 'Aadhar Card'),
        ('Other Document', 'Other Document'),
    ]
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='faculty/documents/', null=True, blank=True)
    file_name = models.CharField(max_length=255, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)

    class Meta:
        db_table = 'faculty_documents'
        constraints = [
            models.UniqueConstraint(fields=['faculty', 'document_type'], name='unique_faculty_document_type')
        ]

    def __str__(self):
        return f"{self.document_type} - {self.faculty.user.get_full_name()}"

class SubjectAllotment(models.Model):
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.CASCADE, related_name='allotments')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='allotments')
    session = models.CharField(max_length=20, default='2025-26')
    theory_hours_per_week = models.IntegerField(default=0)
    lab_hours_per_week = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'subject_allotments'
        unique_together = ('faculty', 'subject', 'session')

    def __str__(self):
        return f"{self.subject.subject_name} - {self.faculty.user.get_full_name()}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            SyllabusCoverage.objects.get_or_create(allotment=self)

    def session_count(self):
        return self.schedules.count()
    session_count.short_description = "Sessions"

    @property
    def semester(self):
        return self.subject.semester
    semester.fget.short_description = "Semester"

    def get_weekly_hours(self):
        """Calculate total hours from related schedules."""
        total_minutes = 0
        for session in self.schedules.all():
            if session.start_time and session.end_time:
                # Simple duration calculation
                start = session.start_time.hour * 60 + session.start_time.minute
                end = session.end_time.hour * 60 + session.end_time.minute
                total_minutes += (end - start)
        return round(total_minutes / 60, 2)

class SubjectSchedule(models.Model):
    DAYS = [
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
        (6, 'Saturday'),
    ]
    SESSION_TYPES = [
        ('Theory', 'Theory'),
        ('Lab', 'Practical/Lab'),
        ('Tutorial', 'Tutorial'),
    ]
    allotment = models.ForeignKey(SubjectAllotment, on_delete=models.CASCADE, related_name='schedules')
    day = models.IntegerField(choices=DAYS)
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES, default='Theory')
    start_time = models.TimeField()
    end_time = models.TimeField()
    room_number = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = 'subject_schedules'
        ordering = ['day', 'start_time']

    def __str__(self):
        return f"{self.get_day_display()}: {self.start_time} - {self.end_time}"

class SyllabusCoverage(models.Model):
    allotment = models.OneToOneField(SubjectAllotment, on_delete=models.CASCADE, related_name='coverage')
    completed_topics = models.ManyToManyField(SubjectTopic, blank=True)
    percentage = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    topics_covered = models.TextField(null=True, blank=True, help_text="Specific notes on coverage")

    class Meta:
        db_table = 'syllabus_coverage'

    def __str__(self):
        return f"{self.allotment.subject.subject_name}: {self.percentage}%"

    def update_percentage(self):
        """Calculate and update percentage based on completed topics."""
        total_topics = self.allotment.subject.topics.count()
        if total_topics > 0:
            completed_count = self.completed_topics.count()
            self.percentage = int((completed_count / total_topics) * 100)
            self.save()
        return self.percentage

class ResearchPublication(models.Model):
    PUB_TYPES = [
        ('Journal', 'Journal Paper'),
        ('Conference', 'Conference Paper'),
        ('Patent', 'Patent'),
        ('Book', 'Book/Chapter'),
    ]
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.CASCADE, related_name='publications')
    title = models.CharField(max_length=500)
    pub_type = models.CharField(max_length=20, choices=PUB_TYPES)
    publication_date = models.DateField()
    link = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'faculty_publications'

    def __str__(self):
        return f"{self.pub_type}: {self.title[:50]}..."

class StudentAttendance(models.Model):
    SESSION_TYPES = [
        ('Theory', 'Theory'),
        ('Lab', 'Practical/Lab'),
    ]
    STATUS_CHOICES = [
        ('P', 'Present'),
        ('A', 'Absent'),
        ('L', 'Leave'),
    ]
    allotment = models.ForeignKey(SubjectAllotment, on_delete=models.CASCADE, related_name='attendance_records')
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(default=timezone.now)
    section = models.CharField(max_length=10, default='A')
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES, default='Theory')
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A')
    marked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='marked_attendance')
    remarks = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'student_attendance'
        unique_together = ('student', 'allotment', 'date', 'section', 'session_type')
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.student.roll_number|default:self.student.enrollment_number} - {self.status} ({self.date})"

class Assignment(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assignments')
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.CASCADE, related_name='created_assignments')
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    attachment = models.FileField(upload_to='assignments/attachments/', null=True, blank=True)
    
    max_points = models.IntegerField(default=10)
    due_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'faculty_assignments'
        ordering = ['-due_date']

    def __str__(self):
        return f"{self.title} ({self.subject.subject_code})"

class FacultyLeaveBalance(models.Model):
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.CASCADE, related_name='leave_balances')
    year = models.IntegerField(default=2026)
    
    cl_total = models.DecimalField(max_digits=5, decimal_places=1, default=12.0)
    cl_used = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    
    sl_total = models.DecimalField(max_digits=5, decimal_places=1, default=10.0)
    sl_used = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    
    al_total = models.DecimalField(max_digits=5, decimal_places=1, default=15.0)
    al_used = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    
    el_total = models.DecimalField(max_digits=5, decimal_places=1, default=14.0)
    el_used = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    
    class Meta:
        db_table = 'faculty_leave_balances'
        unique_together = ('faculty', 'year')

    def __str__(self):
        return f"{self.faculty.user.get_full_name()} ({self.year})"

class FacultyLeave(models.Model):
    LEAVE_TYPES = [
        ('CL', 'Casual Leave'),
        ('SL', 'Sick Leave'),
        ('AL', 'Academic Leave'),
        ('EL', 'Earned Leave'),
        ('OD', 'On Duty'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.CASCADE, related_name='leaves')
    leave_type = models.CharField(max_length=5, choices=LEAVE_TYPES)
    
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    alt_arrangement = models.TextField(null=True, blank=True)
    attachment = models.FileField(upload_to='faculty/leaves/', null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_faculty_leaves')
    remarks = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'faculty_leaves'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.faculty.user.get_full_name()} - {self.leave_type} ({self.status})"
    
    @property
    def duration_days(self):
        return (self.end_date - self.start_date).days + 1
