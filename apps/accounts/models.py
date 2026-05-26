from django.db import models, transaction
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from datetime import datetime

class Permission(models.Model):
    permission_name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'permissions'

    def __str__(self):
        return self.permission_name

class Role(models.Model):
    role_name = models.CharField(max_length=50, unique=True)
    permissions = models.ManyToManyField(Permission, related_name='roles', blank=True)

    class Meta:
        db_table = 'roles'

    def __str__(self):
        return self.role_name

class IDCounter(models.Model):
    """Tracks the last used serial number for specific ID prefixes."""
    prefix = models.CharField(max_length=50, unique=True)
    last_serial = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'id_counter'

    def __str__(self):
        return f"{self.prefix} - {self.last_serial}"


def get_qualification_code(qual_str):
    if not qual_str:
        return 'PH'  # Default to Ph.D
    qual_upper = qual_str.upper()
    if 'PH' in qual_upper or 'DOCTOR' in qual_upper:
        return 'PH'
    if 'M.TECH' in qual_upper or 'MTECH' in qual_upper or 'M.E' in qual_upper or 'ME' in qual_upper:
        # Check if MBA/MCA/M.Sc is there first
        if 'MBA' in qual_upper:
            return 'MB'
        if 'MCA' in qual_upper:
            return 'MS'
        if 'M.SC' in qual_upper or 'MSC' in qual_upper:
            return 'MS'
        return 'MT'
    if 'MBA' in qual_upper or 'PGDM' in qual_upper:
        return 'MB'
    if 'M.SC' in qual_upper or 'MSC' in qual_upper or 'MCA' in qual_upper:
        return 'MS'
    if 'B.TECH' in qual_upper or 'BTECH' in qual_upper or 'B.E' in qual_upper or 'BE' in qual_upper:
        return 'BT'
    
    # fallback: try first 2 characters or default to PH
    clean_qual = ''.join(e for e in qual_upper if e.isalnum())
    if len(clean_qual) >= 2:
        return clean_qual[:2]
    return 'PH'

def get_post_code(role_str, designation_str):
    role_upper = str(role_str).upper()
    desig_upper = str(designation_str or "").upper()
    
    if role_upper == 'HOD' or 'HOD' in desig_upper or 'HEAD' in desig_upper:
        return 'H'
    if 'PROFESSOR' in desig_upper:
        if 'ASSISTANT' in desig_upper or 'ASST' in desig_upper or 'ASSOCIATE' in desig_upper or 'ASSOC' in desig_upper:
            return 'A'
        return 'P'
    if 'LAB' in desig_upper:
        return 'L'
    if 'TECH' in desig_upper:
        return 'T'
    
    # Default fallbacks based on role
    if role_upper == 'HOD':
        return 'H'
    elif role_upper in ['FACULTY', 'TEACHER']:
        return 'A'
    return 'A'  # fallback

def generate_table_driven_id(role, college_obj=None, academic_code=None, user=None):
    """
    New ID generation logic that uses hierarchy tables.
    """
    year = datetime.now().strftime("%y")
    role_upper = str(role).upper()
    
    # 1. Fetch College Code (zfill to 4 digits as per RGPV/SRCEM standards)
    college_code = college_obj.college_code if college_obj else "0904"
    college_code = str(college_code).zfill(4)
    
    # 2. Build Prefix based on Role
    if role_upper == 'STUDENT':
        # Map branch codes to RGPV/standard 2-character codes if necessary
        branch_map = {
            'CSE': 'CS',
            'ECE': 'EC',
            'MEE': 'ME',
            'CIV': 'CE',
            'EEE': 'EE',
            'EEX': 'EX',
            'INF': 'IT',
            'ME': 'ME',
            'CS': 'CS',
            'EC': 'EC',
            'CE': 'CE',
            'EE': 'EE',
            'IT': 'IT',
        }
        raw_branch = str(academic_code or "CS").upper()
        branch_code = branch_map.get(raw_branch, raw_branch[:2])

        # Admission Year (2 digits)
        year_val = None
        if user:
            year_val = getattr(user, '_academic_year_context', None)
            if not year_val and hasattr(user, 'student_profile') and user.student_profile:
                year_val = user.student_profile.batch_year
        
        if year_val:
            admission_year = str(year_val)[-2:]
        else:
            admission_year = year

        # Admission Type: 1 for Regular, 3 for Lateral Entry
        # Defaults to 1. If semester context is >= 3, set to 3.
        admission_type = "1"
        if user:
            sem_val = getattr(user, '_admission_semester_context', None)
            if not sem_val and hasattr(user, 'student_profile') and user.student_profile:
                sem_val = user.student_profile.semester
                
            if sem_val:
                try:
                    sem_int = int(sem_val)
                    if sem_int >= 3:
                        admission_type = "3"
                except (ValueError, TypeError):
                    pass
            
            # Explicit override if present
            if getattr(user, '_admission_type_context', None):
                admission_type = str(user._admission_type_context)

        # Pattern: College Code (0904) + Branch (CS) + Admission Year (25) + Admission Type (1)
        prefix = f"{college_code}{branch_code}{admission_year}{admission_type}"
    elif role_upper in ['FACULTY', 'TEACHER', 'HOD']:
        # Extract Qualification
        qual_val = None
        if user:
            qual_val = getattr(user, '_qualification_context', None)
            if not qual_val and hasattr(user, 'faculty_profile') and user.faculty_profile:
                qual_val = user.faculty_profile.qualification
        qual_code = get_qualification_code(qual_val)

        # Extract Joining Year (2 digits)
        joining_year = None
        if user:
            jd = getattr(user, '_joining_date_context', None)
            if not jd and hasattr(user, 'faculty_profile') and user.faculty_profile:
                jd = user.faculty_profile.joining_date
            
            if jd:
                if hasattr(jd, 'year'):
                    joining_year = str(jd.year)[-2:]
                else:
                    try:
                        from django.utils.dateparse import parse_date
                        parsed_d = parse_date(str(jd))
                        if parsed_d:
                            joining_year = str(parsed_d.year)[-2:]
                        else:
                            joining_year = str(jd)[:4][-2:]
                    except:
                        pass
        if not joining_year:
            joining_year = year

        # Extract Post Code
        desig_val = None
        if user:
            desig_val = getattr(user, '_designation_context', None)
            if not desig_val and hasattr(user, 'faculty_profile') and user.faculty_profile:
                desig_val = user.faculty_profile.designation
        post_code = get_post_code(role, desig_val)

        # Pattern: College Code (0904) + Qualification Code (PH) + Joining Year (26) + Post Code (A)
        prefix = f"{college_code}{qual_code}{joining_year}{post_code}"
    elif role_upper in ['ADMIN', 'SUB_ADMIN']:
        # Extract Joining Year (2 digits)
        joining_year = None
        if user:
            jd = getattr(user, '_joining_date_context', None)
            if jd:
                if hasattr(jd, 'year'):
                    joining_year = str(jd.year)[-2:]
                else:
                    try:
                        from django.utils.dateparse import parse_date
                        parsed_d = parse_date(str(jd))
                        if parsed_d:
                            joining_year = str(parsed_d.year)[-2:]
                        else:
                            joining_year = str(jd)[:4][-2:]
                    except:
                        pass
        if not joining_year:
            joining_year = year

        # Post Code: M for ADMIN, C for SUB_ADMIN
        post_code = 'M' if role_upper == 'ADMIN' else 'C'

        # Pattern: College Code (0904) + AD + Joining Year (26) + Post Code (M/C)
        prefix = f"{college_code}AD{joining_year}{post_code}"
    elif role_upper in ['ACCOUNTANT', 'ADMISSION']:
        # Extract Joining Year (2 digits)
        joining_year = None
        if user:
            jd = getattr(user, '_joining_date_context', None)
            if jd:
                if hasattr(jd, 'year'):
                    joining_year = str(jd.year)[-2:]
                else:
                    try:
                        from django.utils.dateparse import parse_date
                        parsed_d = parse_date(str(jd))
                        if parsed_d:
                            joining_year = str(parsed_d.year)[-2:]
                        else:
                            joining_year = str(jd)[:4][-2:]
                    except:
                        pass
        if not joining_year:
            joining_year = year

        if role_upper == 'ACCOUNTANT':
            domain = 'AC'
            post_code = 'A'
        else:
            domain = 'FN'
            post_code = 'O'

        # Pattern: College Code (0904) + Domain (AC/FN) + Joining Year (26) + Post Code (A/O)
        prefix = f"{college_code}{domain}{joining_year}{post_code}"
    else:
        suffix = academic_code or "GEN"
        prefix = f"STF{year}{college_code}"

    # 4. Get Serial from IDCounter
    return get_serial_for_prefix(prefix)

def get_serial_for_prefix(prefix):
    with transaction.atomic():
        counter, _ = IDCounter.objects.select_for_update().get_or_create(prefix=prefix)
        counter.last_serial += 1
        counter.save()
        serial_str = str(counter.last_serial).zfill(3)
        return f"{prefix}{serial_str}"

class UserManager(BaseUserManager):
    def create_user(self, login_id=None, password=None, **extra_fields):
        # Allow blank login_id to be generated in save()
        if login_id == "":
            login_id = None
        
        # Ensure 'username' is not passed to the constructor
        extra_fields.pop('username', None)
        user = self.model(login_id=login_id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, login_id, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(login_id, password, **extra_fields)

class User(AbstractUser):
    username = None  # remove default username

    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('SUB_ADMIN', 'Sub Admin'),
        ('STUDENT', 'Student'),
        ('FACULTY', 'Faculty'),
        ('TEACHER', 'Teacher'),
        ('HOD', 'HOD'),
        ('ACCOUNTANT', 'Accountant'),
        ('LIBRARIAN', 'Librarian'),
        ('ADMISSION', 'Admission Officer'),
        ('LAB', 'Lab Assistant'),
        ('PLACEMENT', 'Placement Officer'),
        ('STAFF', 'Staff'),
    ]

    # 🔐 LOGIN ID (AUTO GENERATED)
    login_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    enrollment_id = models.CharField(max_length=50, unique=True, null=True, blank=True)

    # 🎭 ROLE
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    # 🏛️ ID GEN DATA (Hiearchy Tables)
    college = models.ForeignKey('core.College', on_delete=models.PROTECT, related_name='users')

    # 👤 BASIC INFO
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50, blank=True)

    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True)

    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)

    # ⚙️ STATUS
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    two_step_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    # 🔐 AUTH CONFIG
    objects = UserManager()
    USERNAME_FIELD = 'login_id'
    REQUIRED_FIELDS = []

    # 🛡️ RBAC Relationship
    roles = models.ManyToManyField(Role, related_name='users', blank=True)

    def has_role_permission(self, permission_name):
        """Check if any of the user's roles have the specified permission."""
        if self.is_superuser:
            return True
        return self.roles.filter(permissions__permission_name=permission_name).exists()

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['enrollment_id'], name='idx_user_enrollment'),
        ]

    def save(self, *args, **kwargs):
        # Auto-generate login_id if empty for supported roles
        if not self.login_id:
            role_upper = str(self.role).upper()
            if role_upper in ['STUDENT', 'FACULTY', 'TEACHER', 'HOD', 'ADMIN', 'SUB_ADMIN', 'ACCOUNTANT', 'ADMISSION']:
                # The academic_code should be passed in kwargs if available during creation, 
                # or we can try to infer it if we're in a specific context.
                # For now, we use the college link.
                academic_code = getattr(self, '_academic_code_context', None)
                self.login_id = generate_table_driven_id(self.role, self.college, academic_code, user=self)
                
                # Automatically sync enrollment_id with login_id for students if not set
                if role_upper == 'STUDENT' and not self.enrollment_id:
                    self.enrollment_id = self.login_id
            elif self.is_superuser:
                self.login_id = generate_table_driven_id('ADMIN', self.college, user=self)
                
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.login_id or 'NO-ID'} ({self.role})"

    @property
    def is_student_user(self):
        return str(self.role).upper() == 'STUDENT'

    @property
    def is_teacher_user(self):
        return str(self.role).upper() in ['FACULTY', 'HOD', 'TEACHER']

class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    employee_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    
    class Meta:
        db_table = 'staff'

    def __str__(self):
        return f"Staff: {self.user.login_id}"


class SecurityLog(models.Model):
    EVENT_CHOICES = [
        ('LOGIN_SUCCESS', 'Successful Login'),
        ('LOGIN_FAILED', 'Failed Login'),
        ('LOGOUT', 'User Logout'),
        ('PASSWORD_CHANGE', 'Password Change'),
        ('UNAUTHORIZED_ACCESS', 'Unauthorized Access'),
        ('ERROR', 'System Error / Exception'),
        ('SUSPICIOUS', 'Suspicious Activity'),
    ]

    event_type = models.CharField(max_length=50, choices=EVENT_CHOICES)
    login_id = models.CharField(max_length=100, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='security_logs')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    path = models.CharField(max_length=255, null=True, blank=True)
    details = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'security_logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.event_type} - {self.login_id or 'Unknown'} ({self.ip_address}) at {self.timestamp}"

