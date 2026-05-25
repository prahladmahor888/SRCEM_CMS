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
            'nationality', 'category', 'bio'
        ]

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
