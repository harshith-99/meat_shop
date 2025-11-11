from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
<<<<<<< HEAD
=======
from django.utils import timezone
>>>>>>> 12bb8f8 (commit on 11112025)
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
    
class Supplierpay(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    payment_date = models.DateField()
    created_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    payment_mode = models.CharField(
        max_length=20,
        choices=(('cash', 'Cash'), ('online', 'Online')),
        default='cash'
    )
    description = models.TextField(blank=True, null=True)
    delete_status = models.BooleanField(default=False)

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
    customer_name = models.CharField(max_length=100, blank=True)
    customer_phone = models.CharField(max_length=15, blank=True, unique=True, null=True)
    customer_address = models.TextField(blank=True)
    gstin = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        unique=True  # Only unique when not blank
    )

    def __str__(self):
        return self.customer_name or self.customer_phone or "Customer"

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
    token = models.CharField(max_length=50, null=True, blank=True)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
class WholesaleSales(models.Model):
    receipt_no = models.CharField(max_length=20, unique=True)
    sales_date = models.DateField()
    created_date = models.DateTimeField(auto_now_add=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='wholesale_sales_added')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='wholesale_sales_updated', null=True, blank=True)
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='wholesale_sales_deleted', null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    delete_status = models.BooleanField(default=False)
    payment_mode = models.CharField(
        max_length=20,
        choices=(('pending', 'Pending'), ('cash', 'Cash'), ('online', 'Online')),
        default='pending'
    )
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2)

    # def clean(self):
    #     if self.paid_amount > self.grand_total:
    #         raise ValidationError("Paid amount cannot be greater than the grand total.")

class WholesaleSalesDetails(models.Model):
    sales = models.ForeignKey(WholesaleSales, on_delete=models.CASCADE, related_name='details')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    qty = models.PositiveIntegerField()
    net_weight = models.DecimalField(max_digits=10, decimal_places=2)
    token = models.CharField(max_length=50, null=True, blank=True)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)


class Employe(models.Model):
    emp_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    phone_no = models.CharField(max_length=15)
    address = models.TextField()
    ROLE_CHOICES = (
        ('staff', 'Staff'),
        ('manager', 'Manager'),
<<<<<<< HEAD
    )
    role = models.CharField(max_length=20,choices=ROLE_CHOICES, default='staff')
=======
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=20,choices=ROLE_CHOICES, default='staff')
    salary_per_day = models.DecimalField(max_digits=10, decimal_places=2)
>>>>>>> 12bb8f8 (commit on 11112025)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    delete_status = models.BooleanField(default=False)

<<<<<<< HEAD
=======


ATTENDANCE_CHOICES = (
    ('present', 'Present'),
    ('absent',  'Absent'),
    ('halfday', 'Half Day'),
)


class Attendance(models.Model):
    ATTENDANCE_CHOICES = (
        ('present', 'Present'),
        ('absent',  'Absent'),
        ('halfday', 'Half Day'),
    )

    employee   = models.ForeignKey(Employe, on_delete=models.CASCADE)
    date       = models.DateField()
    status     = models.CharField(max_length=10, choices=ATTENDANCE_CHOICES, default='present')
    branch     = models.ForeignKey(Branch, on_delete=models.CASCADE)   # cached for fast filtering
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='attendance_recorded'
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'date')      # one record per employee per day
        ordering = ['-date', 'branch__branch_name', 'employee__name']

    def __str__(self):
        return f"{self.employee.name} – {self.get_status_display()} ({self.date})"

>>>>>>> 12bb8f8 (commit on 11112025)
