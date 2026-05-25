from django import forms
from django.contrib.auth import get_user_model
from apps.core.models import College, Department, Program, Branch, Subject, SubjectTopic
from apps.faculty.models import FacultyProfile, FacultyDocument, SubjectAllotment, SubjectSchedule, SyllabusCoverage

User = get_user_model()

class FacultyStep1AccountForm(forms.ModelForm):
    """Step 1: Account Creation & Institutional Role"""
    role = forms.ChoiceField(
        choices=[(k, v) for k, v in User.ROLE_CHOICES if k not in ['ADMIN', 'SUB_ADMIN', 'STUDENT']],
        required=True,
        label="Select Role"
    )
    academic_department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=True,
        label="Department"
    )
    
    password = forms.CharField(widget=forms.PasswordInput(), required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput(), required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'college', 'profile_image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.FileInput, forms.CheckboxInput)):
                field.widget.attrs.update({'class': 'form-input'}) # Generic class, styling handled in template

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("confirm_password"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

class FacultyStep2ProfessionalForm(forms.ModelForm):
    """Step 2: Professional & Academic Details"""
    joining_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = FacultyProfile
        fields = ['designation', 'qualification', 'joining_date']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-input'})

class FacultyStep3DocumentForm(forms.Form):
    """Step 3: Joining Document Uploads"""
    joining_letter = forms.FileField(label="Joining Letter", required=False)
    resume = forms.FileField(label="Resume/CV", required=False)
    experience_certificate = forms.FileField(label="Experience Certificate", required=False)
    qualification_proof = forms.FileField(label="Qualification Proof (Ph.D/Master’s)", required=False)
    aadhar_card = forms.FileField(label="Aadhar Card", required=False)
    other_document = forms.FileField(label="Other Certificate", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-file-input'})

class SubjectAllotmentForm(forms.ModelForm):
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        required=False,
        label="Filter by Branch",
        empty_label="-- Select Branch --"
    )
    semester = forms.ChoiceField(
        choices=[('', '-- Select Semester --')] + [(i, f"Semester {i}") for i in range(1, 9)],
        required=False,
        label="Filter by Semester"
    )

    class Meta:
        model = SubjectAllotment
        fields = ['branch', 'semester', 'faculty', 'subject', 'session']
        widgets = {
            'session': forms.TextInput(attrs={'placeholder': 'e.g. 2025-26'}),
        }

    def __init__(self, *args, **kwargs):
        department = kwargs.pop('department', None)
        super().__init__(*args, **kwargs)
        
        if department:
            self.fields['faculty'].queryset = FacultyProfile.objects.filter(department=department)
            # Default empty subjects, filtered by AJAX
            self.fields['subject'].queryset = Subject.objects.filter(branch__program__dept=department)
        
        # Set initial values for branch and semester if editing
        if self.instance and self.instance.pk:
            self.fields['branch'].initial = self.instance.subject.branch
            self.fields['semester'].initial = self.instance.subject.semester
        
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-input'})

class SubjectScheduleForm(forms.ModelForm):
    class Meta:
        model = SubjectSchedule
        fields = ['day', 'session_type', 'start_time', 'end_time', 'room_number']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-input'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs.update({'class': 'form-input'})

class SubjectScheduleCreateForm(forms.ModelForm):
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(), 
        required=False, 
        label="Filter by Branch",
        empty_label="--- Select Branch to Filter ---"
    )
    semester = forms.ChoiceField(
        choices=[('', '--- All Semesters ---')] + [(i, f"Semester {i}") for i in range(1, 9)], 
        required=False, 
        label="Filter by Semester"
    )

    class Meta:
        model = SubjectSchedule
        fields = ['branch', 'semester', 'allotment', 'day', 'session_type', 'start_time', 'end_time', 'room_number']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-input'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        department = kwargs.pop('department', None)
        super().__init__(*args, **kwargs)
        
        if department:
            self.fields['branch'].queryset = Branch.objects.filter(program__dept=department)
            self.fields['allotment'].queryset = SubjectAllotment.objects.filter(faculty__department=department)
        
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs.update({'class': 'form-input'})

class SyllabusTopicForm(forms.ModelForm):
    class Meta:
        model = SubjectTopic
        fields = ['unit_number', 'title', 'description', 'order']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-input'})
