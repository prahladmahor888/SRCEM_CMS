from django import forms
from .models import Subject

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['branch', 'subject_name', 'subject_code', 'subject_type', 'credits', 'semester', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply premium styling
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': 'w-full px-4 py-2.5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl text-xs font-bold focus:ring-2 focus:ring-primary/10 focus:border-primary outline-none transition-all dark:text-white'
                })
