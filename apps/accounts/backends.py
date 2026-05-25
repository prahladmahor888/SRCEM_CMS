from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from apps.students.models import Student
from apps.faculty.models import FacultyProfile
from apps.accounts.models import StaffProfile

User = get_user_model()

class MultiIDAuthBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using:
    - Login ID (Primary)
    - Student Enrollment ID
    - Student Roll Number
    - Faculty Employee ID
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            return None
            
        try:
            # 1. Try to find user by standard login_id
            user = User.objects.get(login_id=username)
        except User.DoesNotExist:
            # 2. Try to find user via Student (Enrollment ID or Roll Number)
            try:
                student = Student.objects.get(Q(enrollment_number=username) | Q(roll_number=username))
                user = student.user
            except Student.DoesNotExist:
                # 3. Try to find user via FacultyProfile (Employee ID)
                try:
                    faculty = FacultyProfile.objects.get(employee_id=username)
                    user = faculty.user
                except FacultyProfile.DoesNotExist:
                    # 4. Try to find user via StaffProfile (Employee ID)
                    try:
                        staff = StaffProfile.objects.get(employee_id=username)
                        user = staff.user
                    except StaffProfile.DoesNotExist:
                        return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
