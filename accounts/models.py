from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
# Create your models here.

class Branch(models.Model):
    branch_id = models.AutoField(primary_key=True)
    branch_name = models.CharField(max_length=100)
    branch_address = models.TextField()

    def __str__(self):
        return self.branch_name


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('super_admin','super_admin'),
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('manager', 'Manager'),
    )
    role = models.CharField(max_length=20,choices=ROLE_CHOICES, default='staff')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

class Supplier(models.Model):
    supplier_id = models.AutoField(primary_key=True)
    supplier_name = models.CharField(max_length=100)
    company_name = models.CharField(max_length=150)
    address = models.TextField()
    phone_no = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    gstin = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.supplier_name} - {self.company_name}"

class ItemCategory(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_weight_based = models.BooleanField(default=True)  # True = sold by weight, False = sold by quantity

    def __str__(self):
        return self.name

    def __str__(self):
        return self.category_name

class Item(models.Model):
    category = models.ForeignKey(ItemCategory, on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    price_per_unit_retail = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    price_per_unit_wholesale = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit = models.CharField(max_length=10, choices=[
        ('kg', 'Kilogram'),
        ('pcs', 'Pieces'),
        ('pkt', 'Packet'),
    ])
    stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # weight or qty

    def __str__(self):
        return f"{self.name} ({self.category.category_name})"

class Purchase(models.Model):
    invoice_number = models.CharField(max_length=20, unique=True)
    purchase_date = models.DateField()
    created_date = models.DateTimeField(auto_now_add=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='purchases_added')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='purchases_updated', null=True, blank=True)
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='purchases_deleted', null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    delete_status = models.BooleanField(default=False)

class PurchaseDetail(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='details')
    purchase_type = models.CharField(max_length=50)
    category = models.ForeignKey(ItemCategory, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    qty = models.PositiveIntegerField()
    gross_weight = models.DecimalField(max_digits=10, decimal_places=2)
    empty_weight = models.DecimalField(max_digits=10, decimal_places=2)
    net_weight = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

class Customer(models.Model):
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=15)
    customer_address = models.TextField()
    gstin = models.CharField(max_length=20, unique=True)

class RetailSales(models.Model):
    receipt_no = models.CharField(max_length=20, unique=True)
    sales_date = models.DateField()
    created_date = models.DateTimeField(auto_now_add=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sales_added')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sales_updated', null=True, blank=True)
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sales_deleted', null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    delete_status = models.BooleanField(default=False)
    payment_mode = models.CharField(
        max_length=20,
        choices=(('cash', 'Cash'), ('online', 'Online')),
        default='cash'
    )

class RetailSalesDetails(models.Model):
    sales = models.ForeignKey(RetailSales,on_delete=models.CASCADE, related_name='details')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    qty = models.PositiveIntegerField()
    net_weight = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    