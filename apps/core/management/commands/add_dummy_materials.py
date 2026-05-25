from django.core.management.base import BaseCommand
from apps.core.models import Subject, StudyMaterial, SubjectTopic
from apps.faculty.models import FacultyProfile
import random

class Command(BaseCommand):
    help = 'Adds dummy study materials for testing'

    def handle(self, *args, **kwargs):
        subjects = Subject.objects.all()
        faculty = FacultyProfile.objects.first()

        if not subjects.exists():
            self.stdout.write(self.style.ERROR('No subjects found. Please add subjects first.'))
            return

        if not faculty:
            self.stdout.write(self.style.ERROR('No faculty profile found. Please add a faculty first.'))
            return

        materials_data = [
            {
                'title': 'Unit 1: Introduction to Machine Learning',
                'type': 'notes',
                'desc': 'Comprehensive notes on ML fundamentals.',
                'size': '2.4 MB'
            },
            {
                'title': 'Lecture 4: CSS Flexbox & Grid Layouts',
                'type': 'video',
                'desc': 'Practical guide to modern CSS layouts.',
                'dur': '45 Mins',
                'url': 'https://www.youtube.com/watch?v=rg7Fvvl3yz0'
            },
            {
                'title': 'Assignment 1: Lexical Analysis Programs',
                'type': 'assignments',
                'desc': 'Implement a basic lexer using C/C++.',
                'size': '1.1 MB'
            },
            {
                'title': 'End Sem Exam 2024 - Machine Learning',
                'type': 'pyq',
                'desc': 'Question paper with solved solutions.',
                'size': '3.5 MB'
            },
            {
                'title': 'Unit 2: Syntax Analysis & Parsing',
                'type': 'notes',
                'desc': 'PPT slides covering LL(1) and LR parsing.',
                'size': '5.2 MB'
            }
        ]

        for i, data in enumerate(materials_data):
            # Rotate subjects if multiple exist
            subject = subjects[i % subjects.count()]
            
            material, created = StudyMaterial.objects.get_or_create(
                title=data['title'],
                subject=subject,
                defaults={
                    'faculty': faculty,
                    'material_type': data['type'],
                    'description': data['desc'],
                    'file_size': data.get('size'),
                    'duration': data.get('dur'),
                    'video_url': data.get('url'),
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created material: {material.title}'))
            else:
                self.stdout.write(self.style.WARNING(f'Material already exists: {material.title}'))

        self.stdout.write(self.style.SUCCESS('Successfully added dummy study materials.'))
