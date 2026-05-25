from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User
from apps.core.models import College, HeroSlide
from django.contrib.messages import get_messages

class CMSViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create a college which is required for User creation
        self.college = College.objects.create(
            name="Test College",
            college_code="TC01"
        )
        
        # Create users for different roles
        self.admin_user = User.objects.create_user(
            login_id='ADMIN01',
            password='password123',
            role='ADMIN',
            college=self.college
        )
        self.sub_admin_user = User.objects.create_user(
            login_id='SUBADMIN01',
            password='password123',
            role='SUB_ADMIN',
            college=self.college
        )
        self.student_user = User.objects.create_user(
            login_id='STUDENT01',
            password='password123',
            role='STUDENT',
            college=self.college
        )

        # Create a sample HeroSlide
        self.hero_slide = HeroSlide.objects.create(
            title="Welcome to SRCEM",
            order=1,
            is_active=True,
            button_text="Click Here",
            button_url="https://srcem.ac.in"
        )

    def test_admin_access(self):
        # Log in as ADMIN
        self.client.login(username='ADMIN01', password='password123')
        
        # Access HeroSlide list view
        response = self.client.get(reverse('cms_heroslide_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome to SRCEM")

        # Access HeroSlide create view
        response = self.client.get(reverse('cms_heroslide_create'))
        self.assertEqual(response.status_code, 200)

    def test_sub_admin_access(self):
        # Log in as SUB_ADMIN
        self.client.login(username='SUBADMIN01', password='password123')
        
        # Access HeroSlide list view
        response = self.client.get(reverse('cms_heroslide_list'))
        self.assertEqual(response.status_code, 200)

    def test_student_access_denied(self):
        # Log in as STUDENT
        self.client.login(username='STUDENT01', password='password123')
        
        # Access HeroSlide list view
        response = self.client.get(reverse('cms_heroslide_list'))
        self.assertRedirects(response, reverse('dashboard'), fetch_redirect_response=False)
        
        # Check messages
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Access Denied: You do not have permission to manage website content.", messages)

    def test_anonymous_access_denied(self):
        # Not logged in
        response = self.client.get(reverse('cms_heroslide_list'))
        self.assertRedirects(response, reverse('dashboard'), fetch_redirect_response=False)
        
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Access Denied: You do not have permission to manage website content.", messages)

    def test_crud_operations_as_admin(self):
        self.client.login(username='ADMIN01', password='password123')

        # Create a HeroSlide
        response = self.client.post(reverse('cms_heroslide_create'), {
            'title': 'New Slide',
            'order': 2,
            'is_active': True,
            'button_text': 'Learn More',
            'button_url': 'https://srcem.ac.in/learn',
        })
        self.assertEqual(response.status_code, 302)  # Redirects to success_url
        self.assertEqual(HeroSlide.objects.count(), 2)

        # Update a HeroSlide
        new_slide = HeroSlide.objects.get(title='New Slide')
        response = self.client.post(reverse('cms_heroslide_edit', kwargs={'pk': new_slide.pk}), {
            'title': 'Updated Title',
            'order': 2,
            'is_active': False,
            'button_text': 'Learn More',
            'button_url': 'https://srcem.ac.in/learn',
        })
        self.assertEqual(response.status_code, 302)
        new_slide.refresh_from_db()
        self.assertEqual(new_slide.title, 'Updated Title')
        self.assertFalse(new_slide.is_active)

        # Delete a HeroSlide (GET deletion test)
        response = self.client.get(reverse('cms_heroslide_delete', kwargs={'pk': new_slide.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(HeroSlide.objects.filter(pk=new_slide.pk).exists())
