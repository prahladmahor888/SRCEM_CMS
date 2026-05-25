from django.db import models
from django.conf import settings
from apps.students.models import Student

class FeeReceipt(models.Model):
    PAYMENT_MODES = [
        ('Cash', 'Cash'),
        ('Online', 'UPI / Online'),
        ('Cheque', 'Cheque / DD'),
        ('Bank-Transfer', 'NEFT / RTGS'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_receipts')
    receipt_no = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODES, default='Online')
    transaction_date = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=True)
    remark = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'fee_receipts'
        ordering = ['-transaction_date']

    def __str__(self):
        return f"{self.receipt_no} - {self.student.user.get_full_name()}"

class FinancialExpense(models.Model):
    CATEGORIES = [
        ('Salary', 'Staff Salary'),
        ('Maintenance', 'Campus Maintenance'),
        ('Utility', 'Electricity / Water / Internet'),
        ('Event', 'Campus Events'),
        ('Marketing', 'Advertising / Marketing'),
        ('Other', 'Other Miscellaneous'),
    ]
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORIES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField()
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'financial_expenses'
        ordering = ['-expense_date']

    def __str__(self):
        return f"{self.title} (₹{self.amount})"
