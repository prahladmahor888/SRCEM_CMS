from django.contrib import admin
from .models import FeeReceipt, FinancialExpense

@admin.register(FeeReceipt)
class FeeReceiptAdmin(admin.ModelAdmin):
    list_display = ('receipt_no', 'student', 'amount', 'payment_mode', 'transaction_date', 'is_verified')
    list_filter = ('payment_mode', 'is_verified', 'transaction_date')
    search_fields = ('receipt_no', 'student__user__first_name', 'student__user__last_name', 'student__enrollment_number')

@admin.register(FinancialExpense)
class FinancialExpenseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'amount', 'expense_date')
    list_filter = ('category', 'expense_date')
    search_fields = ('title', 'description')
