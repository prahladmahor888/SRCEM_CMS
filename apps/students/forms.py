from django import forms
from .models import Student

class StudentForm(forms.ModelForm):
    """
    Premium form for Student registry management with 
    standardized dropdown selection for Batch Year.
    """
    batch_year = forms.ChoiceField(
        choices=Student.GET_BATCH_YEAR_CHOICES(),
        required=False,
        label="Batch Year"
    )

    class Meta:
        model = Student
        fields = [
            'user', 'branch', 'enrollment_number', 'roll_number', 
            'semester', 'batch_year', 'status', 'date_of_birth', 
            'gender', 'blood_group', 'phone_alt', 'address', 
            'nationality', 'bio',
            'category', 'fee_category', 'referred_by', 'admission_semester_fee', 'one_time_admission_fee'
        ]

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        fee_category = cleaned_data.get('fee_category')
        
        if category == 'General' and fee_category == 'scholarship_base':
            self.add_error('fee_category', "General category students cannot select the scholarship-based quota.")
            
        if fee_category == 'scholarship_base':
            cleaned_data['admission_semester_fee'] = 0.00
            cleaned_data['one_time_admission_fee'] = 0.00
            
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply premium styling for generic form generator
        for name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'w-full px-4 py-3 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl text-sm font-bold focus:ring-2 focus:ring-primary/10 focus:border-primary outline-none transition-all dark:text-white'
            })
            # Specifically handle select fields (admin-select class for chevron)
            if isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs['class'] += ' admin-select'
