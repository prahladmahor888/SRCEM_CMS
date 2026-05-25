from django.core.management.base import BaseCommand
from apps.faculty.models import FacultyProfile, FacultyLeave, FacultyLeaveBalance
from apps.students.models import Student, StudentLeave
from django.utils import timezone
from datetime import timedelta
import random

class Command(BaseCommand):
    help = 'Adds dummy leave data and balances for testing'

    def handle(self, *args, **kwargs):
        faculty = FacultyProfile.objects.first()
        student = Student.objects.first()

        if not faculty or not student:
            self.stdout.write(self.style.ERROR('Required profiles (Faculty/Student) missing.'))
            return

        # 1. Faculty Balances
        balance, created = FacultyLeaveBalance.objects.get_or_create(
            faculty=faculty,
            year=timezone.now().year,
            defaults={
                'cl_total': 12.0, 'cl_used': 3.0,
                'sl_total': 10.0, 'sl_used': 2.0,
                'al_total': 15.0, 'al_used': 5.0,
                'el_total': 14.0, 'el_used': 0.0
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created leave balance for {faculty.user.get_full_name()}'))

        # 2. Faculty History
        FacultyLeave.objects.get_or_create(
            faculty=faculty,
            leave_type='CL',
            start_date=timezone.now().date() + timedelta(days=5),
            end_date=timezone.now().date() + timedelta(days=6),
            reason='Family function',
            status='Pending'
        )
        FacultyLeave.objects.get_or_create(
            faculty=faculty,
            leave_type='SL',
            start_date=timezone.now().date() - timedelta(days=10),
            end_date=timezone.now().date() - timedelta(days=9),
            reason='Viral fever',
            status='Approved'
        )

        # 3. Student History
        if student.mentor:
            StudentLeave.objects.get_or_create(
                student=student,
                mentor=student.mentor,
                leave_type='Sick Leave',
                start_date=timezone.now().date() + timedelta(days=2),
                end_date=timezone.now().date() + timedelta(days=3),
                reason='Medical checkup',
                status='Pending'
            )
            StudentLeave.objects.get_or_create(
                student=student,
                mentor=student.mentor,
                leave_type='Personal Event',
                start_date=timezone.now().date() - timedelta(days=5),
                end_date=timezone.now().date() - timedelta(days=4),
                reason='Sister marriage',
                status='Approved'
            )

        self.stdout.write(self.style.SUCCESS('Successfully added dummy leave data.'))
