from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Sum
from apps.students.models import Student
from .models import FeeReceipt

class StudentFeeDetailsView(LoginRequiredMixin, View):
    template_name = 'fees/fee_details.html'

    def dispatch(self, request, *args, **kwargs):
        # Direct check for student role
        if not hasattr(request.user, 'is_student_user') or not request.user.is_student_user:
            messages.error(request, "Access Denied: This page is only for students.")
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        try:
            student = request.user.student_profile
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found.")
            return redirect('dashboard')

        # Retrieve all receipts for this student
        receipts = FeeReceipt.objects.filter(student=student).order_by('-transaction_date')
        
        # Calculate total paid amount from verified receipts
        total_paid = receipts.filter(is_verified=True).aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate fees based on the student's agreed admission package
        admission_fee = student.one_time_admission_fee
        tuition_fee = student.admission_semester_fee * student.semester
        total_payable = admission_fee + tuition_fee
        total_due = max(0, total_payable - total_paid)
        total_semesters = (student.branch.duration_years * 2) if (student.branch and student.branch.duration_years) else 8
        total_course_fee = student.one_time_admission_fee + (student.admission_semester_fee * total_semesters)
        
        context = {
            'student': student,
            'receipts': receipts,
            'admission_semester_fee': student.admission_semester_fee,
            'one_time_admission_fee': student.one_time_admission_fee,
            'tuition_fee': tuition_fee,
            'admission_fee': admission_fee,
            'total_payable': total_payable,
            'total_paid': total_paid,
            'total_due': total_due,
            'has_due': total_due > 0,
            'total_semesters': total_semesters,
            'total_course_fee': total_course_fee,
            'module_name': "Fee Registry",
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        try:
            student = request.user.student_profile
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found.")
            return redirect('dashboard')

        amount_str = request.POST.get('amount')
        payment_mode = request.POST.get('payment_mode', 'Online')
        remark = request.POST.get('remarks', '')

        if not amount_str:
            messages.error(request, "Please enter a valid amount.")
            return redirect('student_fees')
        
        try:
            from decimal import Decimal
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            messages.error(request, "Amount must be a positive number.")
            return redirect('student_fees')

        # Check total remaining dues to prevent overpaying
        receipts = FeeReceipt.objects.filter(student=student)
        total_paid = receipts.filter(is_verified=True).aggregate(total=Sum('amount'))['total'] or 0
        total_payable = student.one_time_admission_fee + (student.admission_semester_fee * student.semester)
        total_due = max(0, total_payable - total_paid)

        if amount > total_due:
            messages.error(request, f"Payment amount exceeds outstanding dues (₹{total_due:,.2f}). Please enter a correct amount.")
            return redirect('student_fees')

        # Generate unique receipt number
        import random
        import string
        while True:
            digits = ''.join(random.choices(string.digits, k=8))
            receipt_no = f"REC-{digits}"
            if not FeeReceipt.objects.filter(receipt_no=receipt_no).exists():
                break

        # Create the receipt
        FeeReceipt.objects.create(
            student=student,
            receipt_no=receipt_no,
            amount=amount,
            payment_mode=payment_mode,
            is_verified=True,
            remark=remark
        )

        messages.success(request, f"Mock payment of ₹{amount:,.2f} successful! Receipt {receipt_no} generated.")
        return redirect('student_fees')


from apps.core.views import RolePermissionMixin

class AccountantCollectFeeView(RolePermissionMixin, View):
    template_name = 'fees/collect_fee.html'
    required_permission = None

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and str(user.role).upper() in ['ADMIN', 'SUB_ADMIN', 'ACCOUNTANT']

    def get(self, request, *args, **kwargs):
        students = Student.objects.filter(status='active').select_related('user', 'branch__program').order_by('user__first_name')
        context = {
            'students': students,
            'payment_modes': FeeReceipt.PAYMENT_MODES,
            'module_name': "Fee Registry",
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        student_id = request.POST.get('student')
        amount_str = request.POST.get('amount')
        payment_mode = request.POST.get('payment_mode')
        remark = request.POST.get('remarks', '')

        if not all([student_id, amount_str, payment_mode]):
            messages.error(request, "All fields are required.")
            return redirect('collect_fee')

        try:
            student = Student.objects.get(pk=student_id)
        except Student.DoesNotExist:
            messages.error(request, "Student not found.")
            return redirect('collect_fee')

        try:
            from decimal import Decimal
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            messages.error(request, "Amount must be a positive number.")
            return redirect('collect_fee')

        # Generate unique receipt number
        import random
        import string
        while True:
            digits = ''.join(random.choices(string.digits, k=8))
            receipt_no = f"REC-{digits}"
            if not FeeReceipt.objects.filter(receipt_no=receipt_no).exists():
                break

        # Create the receipt
        FeeReceipt.objects.create(
            student=student,
            receipt_no=receipt_no,
            amount=amount,
            payment_mode=payment_mode,
            is_verified=True,
            remark=remark
        )

        messages.success(request, f"Fee of ₹{amount:,.2f} collected successfully from {student.user.get_full_name()}! Receipt {receipt_no} generated.")
        return redirect('accountant_ledger')


class AccountantLedgerView(RolePermissionMixin, View):
    template_name = 'fees/ledger.html'
    required_permission = None

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and str(user.role).upper() in ['ADMIN', 'SUB_ADMIN', 'ACCOUNTANT', 'HOD']

    def get(self, request, *args, **kwargs):
        receipts = FeeReceipt.objects.select_related('student__user', 'student__branch').all().order_by('-transaction_date')
        
        # Search query
        q = request.GET.get('q', '').strip()
        if q:
            from django.db.models import Q
            receipts = receipts.filter(
                Q(receipt_no__icontains=q) |
                Q(student__user__first_name__icontains=q) |
                Q(student__user__last_name__icontains=q) |
                Q(student__enrollment_number__icontains=q)
            )

        # Payment Mode Filter
        mode = request.GET.get('mode', '').strip()
        if mode:
            receipts = receipts.filter(payment_mode=mode)

        context = {
            'receipts': receipts,
            'payment_modes': FeeReceipt.PAYMENT_MODES,
            'search_query': q,
            'selected_mode': mode,
            'module_name': "Fee Registry",
        }
        return render(request, self.template_name, context)


class FeeStructureView(RolePermissionMixin, View):
    template_name = 'fees/fee_structure.html'

    def test_func(self):
        return self.request.user.is_authenticated

    def get(self, request, *args, **kwargs):
        from apps.core.models import Branch
        
        branches = Branch.objects.select_related('program__dept').all().order_by('program__program_name', 'branch_name')
        
        structures = []
        for b in branches:
            prog_code = (b.program.program_code or '').upper() if b.program else ''
            
            # Map standard fees based on program code
            if 'B.TECH' in prog_code or 'B.E.' in prog_code:
                sem_fee = 75000.00
                one_time = 5000.00
            elif 'M.TECH' in prog_code or 'M.E.' in prog_code:
                sem_fee = 60000.00
                one_time = 5000.00
            elif 'MBA' in prog_code:
                sem_fee = 65000.00
                one_time = 5000.00
            elif 'BCA' in prog_code or 'BBA' in prog_code:
                sem_fee = 45000.00
                one_time = 4000.00
            elif 'DIPLOMA' in prog_code or 'POLY' in prog_code:
                sem_fee = 30000.00
                one_time = 3000.00
            else:
                sem_fee = 50000.00
                one_time = 4000.00
                
            total_semesters = b.duration_years * 2
            total_fee = (sem_fee * total_semesters) + one_time
            
            structures.append({
                'id': b.id,
                'program': b.program.program_name if b.program else 'N/A',
                'program_code': prog_code,
                'branch_name': b.branch_name,
                'branch_code': b.branch_code or 'N/A',
                'duration': f"{b.duration_years} Years ({total_semesters} Semesters)",
                'semester_fee': sem_fee,
                'one_time_fee': one_time,
                'total_fee': total_fee
            })
            
        context = {
            'fee_structures': structures,
            'module_name': "Fee Registry",
        }
        return render(request, self.template_name, context)


class StudentPaymentFormView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            student = request.user.student_profile
        except Student.DoesNotExist:
            from django.http import HttpResponse
            return HttpResponse("Student profile not found.", status=404)

        receipts = FeeReceipt.objects.filter(student=student)
        total_paid = receipts.filter(is_verified=True).aggregate(total=Sum('amount'))['total'] or 0
        total_payable = student.one_time_admission_fee + (student.admission_semester_fee * student.semester)
        total_due = max(0, total_payable - total_paid)

        context = {
            'total_due': total_due,
        }
        return render(request, 'fees/forms/payment_form.html', context)



