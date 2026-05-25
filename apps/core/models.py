from django.db import models

class College(models.Model):
    name = models.CharField(max_length=255)
    college_code = models.CharField(max_length=50, unique=True)
    address = models.TextField(null=True, blank=True)
    website = models.URLField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'college'

    def __str__(self):
        return f"{self.name} ({self.college_code})"

class CollegeSettings(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='settings')
    setting_key = models.CharField(max_length=50) # e.g., 'logo_url', 'current_session'
    setting_value = models.TextField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'college_settings'
        verbose_name_plural = "College Settings"

    def __str__(self):
        return f"{self.college.college_code}: {self.setting_key}"

class Department(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='departments')
    dept_name = models.CharField(max_length=100)
    dept_code = models.CharField(max_length=20, unique=True, null=True, blank=True)

    class Meta:
        db_table = 'departments'

    def __str__(self):
        return self.dept_name

class Program(models.Model):
    dept = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='programs')
    program_name = models.CharField(max_length=100) # e.g., 'Bachelor of Technology'
    program_code = models.CharField(max_length=20, unique=True, null=True, blank=True) # e.g., 'B.Tech'

    class Meta:
        db_table = 'programs'

    def __str__(self):
        return f"{self.program_name} ({self.program_code})"

class Branch(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='branches', null=True, blank=True)
    branch_name = models.CharField(max_length=100)
    branch_code = models.CharField(max_length=20, unique=True, null=True, blank=True)
    duration_years = models.IntegerField(default=4)

    class Meta:
        db_table = 'branches'
        verbose_name_plural = "Branches"

    def __str__(self):
        return self.branch_name

class Subject(models.Model):
    SUBJECT_TYPES = [
        ('theory', 'Theory'),
        ('practical', 'Practical'),
        ('project', 'Project'),
        ('elective', 'Elective'),
    ]
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='subjects')
    subject_name = models.CharField(max_length=255)
    subject_code = models.CharField(max_length=50, unique=True)
    subject_type = models.CharField(max_length=20, choices=SUBJECT_TYPES, default='theory')
    credits = models.IntegerField(default=3)
    semester = models.IntegerField() # Which semester this subject is taught in
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'subjects'
        verbose_name_plural = "Subjects"

    def __str__(self):
        return f"{self.subject_name} ({self.subject_code})"

class SubjectTopic(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='topics')
    unit_number = models.IntegerField(default=1)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        db_table = 'subject_topics'
        ordering = ['unit_number', 'order']

    def __str__(self):
        return f"U{self.unit_number}: {self.title}"

class ExamSchedule(models.Model):
    EXAM_TYPES = [
        ('Theory', 'Theory Exam'),
        ('Practical', 'Practical Exam'),
        ('Viva', 'Viva Voce'),
    ]
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exam_schedules')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    venue = models.CharField(max_length=100)
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPES, default='Theory')
    
    class Meta:
        db_table = 'exam_schedules'
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.subject.subject_name} Exam ({self.date})"

class StudyMaterial(models.Model):
    MATERIAL_TYPES = [
        ('notes', 'Lecture Notes (PDF/PPT)'),
        ('assignments', 'Assignments'),
        ('video', 'Video Lectures'),
        ('pyq', 'Previous Year Papers'),
    ]
    
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='materials')
    faculty = models.ForeignKey('faculty.FacultyProfile', on_delete=models.SET_NULL, null=True, related_name='uploaded_materials')
    
    title = models.CharField(max_length=255)
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPES)
    
    # Storage
    file = models.FileField(upload_to='study_materials/', null=True, blank=True)
    video_url = models.URLField(max_length=500, null=True, blank=True)
    
    # Metadata
    description = models.TextField(null=True, blank=True)
    file_size = models.CharField(max_length=50, null=True, blank=True) # e.g. 2.4 MB
    duration = models.CharField(max_length=50, null=True, blank=True) # e.g. 45 Mins
    
    is_active = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'study_materials'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} ({self.subject.subject_code})"

class PublicNotice(models.Model):
    NOTICE_TYPES = [
        ('announcement', 'Announcement'),
        ('circular', 'Circular'),
    ]
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, null=True)
    notice_type = models.CharField(max_length=20, choices=NOTICE_TYPES, default='announcement')
    link_url = models.URLField(max_length=500, blank=True, null=True, help_text="Optional link to a document or webpage")
    is_popup = models.BooleanField(default=False, help_text="Show this as a popup alert on the homepage.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'public_notices'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_notice_type_display()}] {self.title}"


class HeroSlide(models.Model):
    title = models.CharField(max_length=255)
    subtitle = models.TextField(blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, null=True, help_text="Image URL for slide background")
    image = models.ImageField(upload_to='hero_slides/', blank=True, null=True, help_text="Or upload image file")
    button_text = models.CharField(max_length=100, default="Apply Now")
    button_url = models.CharField(max_length=255, default="#")
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'hero_slides'
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

    @property
    def get_image_url(self):
        if self.image:
            return self.image.url
        return self.image_url or ""


class CollegeEvent(models.Model):
    title = models.CharField(max_length=255)
    event_date = models.DateField()
    venue = models.CharField(max_length=255, default="Main Auditorium, SRCEM")
    image_url = models.URLField(max_length=500, blank=True, null=True)
    image = models.ImageField(upload_to='events/', blank=True, null=True)
    link_url = models.URLField(max_length=500, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'college_events'
        ordering = ['-event_date']

    def __str__(self):
        return self.title

    @property
    def get_image_url(self):
        if self.image:
            return self.image.url
        return self.image_url or ""


class HomeProgram(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    image_url = models.URLField(max_length=500, blank=True, null=True)
    image = models.ImageField(upload_to='programs/', blank=True, null=True)
    icon_class = models.CharField(max_length=100, default="fa-solid fa-microchip", help_text="FontAwesome icon class")
    link_url = models.CharField(max_length=255, default="#")
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'home_programs'
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

    @property
    def get_image_url(self):
        if self.image:
            return self.image.url
        return self.image_url or ""


class GalleryItem(models.Model):
    title = models.CharField(max_length=150, blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    image = models.ImageField(upload_to='gallery/', blank=True, null=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gallery_items'
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title or f"Gallery Item {self.id}"

    @property
    def get_image_url(self):
        if self.image:
            return self.image.url
        return self.image_url or ""


class Recruiter(models.Model):
    name = models.CharField(max_length=100)
    logo_url = models.URLField(max_length=500, blank=True, null=True)
    logo = models.ImageField(upload_to='recruiters/', blank=True, null=True)
    icon_class = models.CharField(max_length=100, blank=True, null=True, help_text="FontAwesome brand icon class, e.g. fa-brands fa-aws")
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'recruiters'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    @property
    def get_logo_url(self):
        if self.logo:
            return self.logo.url
        return self.logo_url or ""


class CollegeStat(models.Model):
    value = models.CharField(max_length=50) # e.g. "25+"
    label = models.CharField(max_length=100) # e.g. "Years Legacy"
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'college_stats'
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.value} - {self.label}"


class AboutSectionConfig(models.Model):
    title = models.CharField(max_length=255, default="Tradition of Excellence")
    subtitle = models.CharField(max_length=100, default="Discover SRCEM")
    description_1 = models.TextField()
    description_2 = models.TextField(blank=True, null=True)
    main_image_url = models.URLField(max_length=500, blank=True, null=True)
    main_image = models.ImageField(upload_to='about/', blank=True, null=True)
    overlap_image_url = models.URLField(max_length=500, blank=True, null=True)
    overlap_image = models.ImageField(upload_to='about/', blank=True, null=True)
    director_name = models.CharField(max_length=150, default="Dr. R. K. Sharma")
    director_designation = models.CharField(max_length=100, default="Director, SRCEM")
    director_photo_url = models.URLField(max_length=500, blank=True, null=True)
    director_photo = models.ImageField(upload_to='about/', blank=True, null=True)
    director_message = models.TextField()
    button_text = models.CharField(max_length=100, default="Read More About Us")
    button_url = models.CharField(max_length=255, default="#")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'about_section_config'
        verbose_name = "About Section Configuration"
        verbose_name_plural = "About Section Configurations"

    def __str__(self):
        return f"About Section Config: {self.title}"

    @property
    def get_main_image_url(self):
        if self.main_image:
            return self.main_image.url
        return self.main_image_url or ""

    @property
    def get_overlap_image_url(self):
        if self.overlap_image:
            return self.overlap_image.url
        return self.overlap_image_url or ""

    @property
    def get_director_photo_url(self):
        if self.director_photo:
            return self.director_photo.url
        return self.director_photo_url or ""


class PlacementConfig(models.Model):
    banner_title = models.CharField(max_length=255, default="Shaping Global Careers")
    banner_subtitle = models.TextField(default="SRCEM Placement Cell works tirelessly to bridge the gap between academia and industry. Hamara focus har student ko sahi platform dene par hai.")
    highest_package = models.CharField(max_length=50, default="45 LPA")
    highest_package_company = models.CharField(max_length=150, default="Offered by Amazon")
    average_package = models.CharField(max_length=50, default="6.5 LPA")
    average_package_batch = models.CharField(max_length=150, default="For Batch 2025")
    total_offers = models.CharField(max_length=50, default="850+")
    total_offers_label = models.CharField(max_length=150, default="Unique Placements")
    total_recruiters = models.CharField(max_length=50, default="120+")
    total_recruiters_label = models.CharField(max_length=150, default="MNCs & Startups")
    training_title = models.CharField(max_length=255, default="Pre-Placement Training & Industry Readiness")
    training_description = models.TextField(default="SRCEM training cell focus karta hai students ki overall growth par. Hum starting se hi technical skills, aptitude, aur soft-skills classes provide karte hain taaki student kisi bhi interview mein confident feel kare.")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'placement_config'
        verbose_name = "Placement Configuration"
        verbose_name_plural = "Placement Configurations"

    def __str__(self):
        return f"Placement Config: {self.banner_title}"


class PlacementAchiever(models.Model):
    student_name = models.CharField(max_length=150)
    company_name = models.CharField(max_length=100)
    package = models.CharField(max_length=50, default="6.5 LPA")
    branch = models.CharField(max_length=100, default="B.Tech (CSE)")
    image_url = models.URLField(max_length=500, blank=True, null=True)
    image = models.ImageField(upload_to='placements/', blank=True, null=True)
    placed_year = models.IntegerField(default=2025)
    is_highest = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'placement_achievers'
        ordering = ['order', '-package', 'id']

    def __str__(self):
        return f"{self.student_name} - {self.company_name} ({self.package})"

    @property
    def get_image_url(self):
        if self.image:
            return self.image.url
        return self.image_url or ""


class PlacementTrainingFeature(models.Model):
    title = models.CharField(max_length=255)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'placement_training_features'
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


class PlacementProcessStep(models.Model):
    step_number = models.IntegerField(default=1)
    title = models.CharField(max_length=150)
    description = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'placement_process_steps'
        ordering = ['step_number', 'id']

    def __str__(self):
        return f"Step {self.step_number}: {self.title}"

