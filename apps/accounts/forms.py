from django import forms
from .models import User
from apps.core.models import Department, Branch
from apps.students.models import Student
from apps.faculty.models import FacultyProfile

class UserCreationForm(forms.ModelForm):
    # --- ACADEMIC CONTEXT (Common) ---
    academic_department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        label="Select Department",
        help_text="For Faculty/Teachers/HODs"
    )
    academic_branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        required=False,
        label="Select Branch",
        help_text="For Students"
    )

    # --- FACULTY SPECIFIC FIELDS ---
    designation = forms.CharField(max_length=100, required=False, label="Designation")
    qualification = forms.CharField(max_length=255, required=False, label="Qualification")
    joining_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}), 
        required=False, 
        label="Joining Date"
    )

    # --- STUDENT SPECIFIC FIELDS ---
    roll_number = forms.CharField(max_length=50, required=False, label="Roll Number")
    semester = forms.IntegerField(required=False, label="Current Semester", min_value=1, max_value=8)
    batch_year = forms.ChoiceField(
        choices=Student.GET_BATCH_YEAR_CHOICES(),
        required=False,
        label="Batch Year"
    )
    admission_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}), 
        required=False, 
        label="Admission Date"
    )
    
    # --- GENERIC STAFF FIELDS ---
    employee_id = forms.CharField(max_length=50, required=False, label="Employee ID")
    staff_department = forms.CharField(max_length=100, required=False, label="Staff Department", help_text="e.g. Accounts, Admission Cell")

    # --- PASSWORD ---
    password = forms.CharField(
        widget=forms.PasswordInput(),
        required=True,
        label="Password",
        help_text="Set an initial password for the user"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(),
        required=True,
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = [
            'role', 'academic_branch', 'academic_department',
            'college', 'first_name', 'last_name', 
            'email', 'phone', 'is_active', 'is_staff',
            'password', 'profile_image'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply premium styling
        for name, field in self.fields.items():
            if not isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({
                    'class': 'w-full px-4 py-3 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl text-sm font-bold focus:ring-2 focus:ring-primary/10 focus:border-primary outline-none transition-all dark:text-white'
                })
            else:
                # Custom file input handling is in the template
                pass

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        
        # Role specific validation
        role = cleaned_data.get('role')
        if role == 'STUDENT' and not cleaned_data.get('academic_branch'):
            self.add_error('academic_branch', "Academic Branch is required for students.")
        elif role in ['FACULTY', 'HOD', 'TEACHER'] and not cleaned_data.get('academic_department'):
            self.add_error('academic_department', "Department is required for faculty.")
            
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user
