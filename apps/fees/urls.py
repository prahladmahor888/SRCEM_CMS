from django.urls import path
from . import views

urlpatterns = [
    path('my-fees/', views.StudentFeeDetailsView.as_view(), name='student_fees'),
    path('collect-fee/', views.AccountantCollectFeeView.as_view(), name='collect_fee'),
    path('ledger/', views.AccountantLedgerView.as_view(), name='accountant_ledger'),
    path('fee-structure/', views.FeeStructureView.as_view(), name='fee_structure'),
]