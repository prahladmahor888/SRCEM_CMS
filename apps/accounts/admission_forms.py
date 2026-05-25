from django import forms
from django.contrib.auth import get_user_model
from apps.core.models import College, Department, Program, Branch
from apps.students.models import Student, Guardian, Document

User = get_user_model()

class Step1AccountForm(forms.ModelForm):
    """Step 1: Account Creation & Academic Context"""
    academic_department = forms.ModelChoiceField(queryset=Department.objects.all(), required=True)
    academic_program = forms.ModelChoiceField(queryset=Program.objects.all(), required=True)
    academic_branch = forms.ModelChoiceField(queryset=Branch.objects.all(), required=True)
    
    password = forms.CharField(widget=forms.PasswordInput(), required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput(), required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'college']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-input'})

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("confirm_password"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

class Step2ProfileForm(forms.ModelForm):
    """Step 2: Student Personal & Guardian Info"""
    # Student fields
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    gender = forms.ChoiceField(choices=Student.GENDER_CHOICES)
    blood_group = forms.ChoiceField(choices=Student.BLOOD_GROUP_CHOICES, required=False)
    category = forms.ChoiceField(choices=Student.CATEGORY_CHOICES, required=False)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
    
    # Guardian fields (included for combined form handling)
    guardian_name = forms.CharField(max_length=100)
    guardian_relation = forms.ChoiceField(choices=Guardian.RELATION_CHOICES)
    guardian_phone = forms.CharField(max_length=15)
    guardian_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=False)

    batch_year = forms.ChoiceField(
        choices=Student.GET_BATCH_YEAR_CHOICES(),
        required=False,
        label="Batch Year"
    )

    class Meta:
        model = Student
        fields = [
            'roll_number', 'semester', 'admission_date', 'batch_year',
            'date_of_birth', 'gender', 'blood_group', 'phone_alt',
            'address', 'nationality', 'category', 'bio'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-input'})
        # Specifically for date fields
        if 'admission_date' in self.fields:
            self.fields['admission_date'].widget = forms.DateInput(attrs={'type': 'date', 'class': 'form-input'})

class Step3DocumentForm(forms.Form):
    """Step 3: Document Uploads"""
    marksheet_10th = forms.FileField(label="10th Marksheet", required=False)
    marksheet_12th = forms.FileField(label="12th Marksheet", required=False)
    aadhar_card = forms.FileField(label="Aadhar Card", required=False)
    caste_certificate = forms.FileField(label="Caste Certificate (Jati)", required=False)
    domicile_certificate = forms.FileField(label="Domicile Certificate (Mool Niwas)", required=False)
    tc_certificate = forms.FileField(label="Transfer Certificate (TC)", required=False)
    other_document = forms.FileField(label="Other Certificate", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-file-input'})
