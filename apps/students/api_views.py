from django.views import View
from django.http import JsonResponse
from apps.core.views import RolePermissionMixin
from .services import BulkAdmissionService
from apps.core import excel_utils as pd
import logging

logger = logging.getLogger(__name__)

class BulkAdmissionAPIView(RolePermissionMixin, View):
    """
    Production-ready API for bulk student admission via Excel upload.
    Only Admin/Superuser access allowed.
    Uses standard Django views to avoid external dependencies.
    """
    required_permission = 'can_manage_users'

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        # Standard Django doesn't have request.data, use request.POST
        dry_run = request.POST.get('dry_run', 'false').lower() == 'true'
        update_existing = request.POST.get('update_existing', 'false').lower() == 'true'

        if not file_obj:
            return JsonResponse({
                "status": "failed", 
                "errors": [{"message": "No file uploaded"}]
            }, status=400)

        if not file_obj.name.lower().endswith(('.xlsx', '.xls')):
            return JsonResponse({
                "status": "failed", 
                "errors": [{"message": "Invalid file format. Use .xlsx"}]
            }, status=400)

        try:
            # Parse all sheets
            dfs = pd.read_excel(file_obj, sheet_name=None)
            
            # Basic structure validation
            BulkAdmissionService.validate_excel_structure(dfs)
            
            # Execute logic
            results = BulkAdmissionService.execute_import(
                dfs, 
                dry_run=dry_run, 
                update_existing=update_existing
            )
            
            status_code = 201 if (results['status'] == 'success' and not dry_run) else 200
            if results['status'] == 'failed':
                status_code = 400
                
            return JsonResponse(results, status=status_code)

        except Exception as e:
            logger.exception("API Bulk admission failed")
            return JsonResponse({
                "status": "failed",
                "errors": [{"sheet": "system", "row": 0, "message": str(e)}]
            }, status=500)
