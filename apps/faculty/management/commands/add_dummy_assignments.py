from django.core.management.base import BaseCommand
from apps.core.models import Subject
from apps.faculty.models import FacultyProfile, Assignment
from apps.students.models import Student, AssignmentSubmission
from django.utils import timezone
from datetime import timedelta
import random

class Command(BaseCommand):
    help = 'Adds dummy assignments and submissions for testing'

    def handle(self, *args, **kwargs):
        subjects = Subject.objects.all()
        faculty = FacultyProfile.objects.first()
        student = Student.objects.first()

        if not subjects.exists() or not faculty or not student:
            self.stdout.write(self.style.ERROR('Required data (Subject, Faculty, Student) missing.'))
            return

        assignments_data = [
            {
                'title': 'Regression Models Implementation',
                'subject': subjects[0],
                'desc': 'Implement Linear and Logistic regression models on house pricing dataset.',
                'due': timezone.now() + timedelta(days=2),
                'points': 20
            },
            {
                'title': 'Responsive Dashboard UI',
                'subject': subjects[min(1, subjects.count()-1)],
                'desc': 'Create a high-fidelity dashboard using Tailwind CSS and standard JS.',
                'due': timezone.now() - timedelta(days=2),
                'points': 10,
                'submit': True # Already submitted
            },
            {
                'title': 'Lexical Analyzer Construction',
                'subject': subjects[min(2, subjects.count()-1)],
                'desc': 'Build a C++ lexer for a subset of the C language.',
                'due': timezone.now() - timedelta(days=5),
                'points': 10,
                'grade': True # Graded
            }
        ]

        for data in assignments_data:
            assignment, created = Assignment.objects.get_or_create(
                title=data['title'],
                subject=data['subject'],
                defaults={
                    'faculty': faculty,
                    'description': data['desc'],
                    'due_date': data['due'],
                    'max_points': data['points']
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created assignment: {assignment.title}'))
            
            if data.get('submit') or data.get('grade'):
                submission, s_created = AssignmentSubmission.objects.get_or_create(
                    assignment=assignment,
                    student=student,
                    defaults={
                        'status': 'submitted' if data.get('submit') else 'graded',
                        'points_obtained': 9.0 if data.get('grade') else None,
                        'remarks': 'Excellent work on the parser!' if data.get('grade') else None
                    }
                )
                if s_created:
                    self.stdout.write(self.style.SUCCESS(f'Created submission for: {assignment.title}'))

        self.stdout.write(self.style.SUCCESS('Successfully added dummy assignments and submissions.'))
