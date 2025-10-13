from django.contrib import admin
from .models import Supplier
from .models import Branch

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("supplier_id", "supplier_name", "company_name", "phone_no", "email", "gstin")
    search_fields = ("supplier_name", "company_name", "gstin")
