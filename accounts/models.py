from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone
# Create your models here.

class Branch(models.Model):
    branch_id = models.AutoField(primary_key=True)
    branch_name = models.CharField(max_length=100)
    alias  = models.CharField(max_length=10)
    branch_address = models.TextField()
    branch_address_full = models.TextField(null=True, blank=True)
    phone = models.CharField(max_length=100, null=True, blank=True)
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
    email = models.EmailField(blank=True, null=True)
    gstin = models.CharField(blank=True, null=True)

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
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)

class ItemCategory(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_weight_based = models.BooleanField(default=True)  # True = sold by weight, False = sold by quantity
    include_in_stock_update = models.BooleanField(default=False)

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
    is_live = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.category.category_name})"

class Purchase(models.Model):
    invoice_number = models.CharField(max_length=20, unique=True)
    purchase_date = models.DateField()
    created_date = models.DateTimeField(auto_now_add=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, default=0)
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
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=3,default='0.000')
    purchase_price = models.DecimalField(max_digits=10, decimal_places=3,default='0.000')
    qty = models.PositiveIntegerField()
    no_of_boxes = models.PositiveIntegerField(blank=True,null=True)
    gross_weight = models.DecimalField(max_digits=10, decimal_places=3,default='0.000')
    empty_weight = models.DecimalField(max_digits=10, decimal_places=3,default='0.000')
    net_weight = models.DecimalField(max_digits=10, decimal_places=3,default='0.000')
    total_amount = models.DecimalField(max_digits=12, decimal_places=3,default='0.000')

class Customer(models.Model):
    customer_name = models.CharField(max_length=100, blank=True)
    customer_phone = models.CharField(max_length=15, blank=True, unique=True, null=True)
    customer_address = models.TextField(blank=True)
    gstin = models.CharField(
        max_length=15,
        blank=True,
        null=True,
    )
    whole_sale = models.BooleanField(default=False)
    opening_balance = models.DecimalField(max_digits=10, decimal_places=3,default='0.000')
    delete_status = models.BooleanField(default=False)
    def __str__(self):
        return self.customer_name or self.customer_phone or "Customer"
    
class Employe(models.Model):
    emp_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    phone_no = models.CharField(max_length=15)
    address = models.TextField()
    ROLE_CHOICES = (
        ('staff', 'Staff'),
        ('manager', 'Manager'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=20,choices=ROLE_CHOICES, default='staff')
    salary_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    delete_status = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class RetailSales(models.Model):
    receipt_no = models.CharField(max_length=20)
    sales_date = models.DateField()
    created_date = models.DateTimeField(auto_now_add=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, default=0)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sales_added')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sales_updated', null=True, blank=True)
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sales_deleted', null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    delete_status = models.BooleanField(default=False)
    payment_mode = models.CharField(
        max_length=20,
        choices=(('cash', 'Cash'), ('upi', 'UPI'),('card', 'Card'),('multiple', 'Multiple'),('pending', 'Pending')),
        default='cash'
    )
    take_amay_employee = models.ForeignKey(Employe, on_delete=models.PROTECT, null=True, blank=True)
    pending_amount = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, default=0)
    total_cash = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, default=0)
    total_upi = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, default=0)
    total_card = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, default=0)

class RetailSalesDetails(models.Model):
    sales = models.ForeignKey(RetailSales,on_delete=models.CASCADE, related_name='details')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    qty = models.PositiveIntegerField()
    net_weight = models.DecimalField(max_digits=10, decimal_places=3,default='0.000')
    token = models.CharField(max_length=50, null=True, blank=True)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=3,default='0.000')
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=3,default='0.000')
    total_amount = models.DecimalField(max_digits=12, decimal_places=3,default='0.000')
    
class WholesaleSales(models.Model):
    receipt_no = models.CharField(max_length=20)
    sales_date = models.DateField()
    created_date = models.DateTimeField(auto_now_add=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, default=0)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='wholesale_sales_added')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='wholesale_sales_updated', null=True, blank=True)
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='wholesale_sales_deleted', null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    delete_status = models.BooleanField(default=False)
    payment_mode = models.CharField(
        max_length=20,
        choices=(('credit', 'Credit'), ('cash', 'Cash'), ('online', 'Online')),
        default='credit'
    )
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2)
    pending_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # def clean(self):
    #     if self.paid_amount > self.grand_total:
    #         raise ValidationError("Paid amount cannot be greater than the grand total.")

class WholesaleSalesDetails(models.Model):
    sales = models.ForeignKey(WholesaleSales, on_delete=models.CASCADE, related_name='details')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    qty = models.PositiveIntegerField()
    net_weight = models.DecimalField(max_digits=10, decimal_places=3,default='0.000')
    token = models.CharField(max_length=50, null=True, blank=True)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=3,default='0.000')
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=3,default='0.000')
    total_amount = models.DecimalField(max_digits=12, decimal_places=3,default='0.000')


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

class WholesalePayment(models.Model):
    receipt_no = models.CharField(max_length=20,default=0)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, limit_choices_to={'whole_sale': True})
    payment_date = models.DateField()
    created_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_mode = models.CharField(
        max_length=20,
        choices=(('cash', 'Cash'), ('upi', 'UPI'), ('online', 'Online'), ('cheque', 'Cheque')),
        default='cash'
    )
    description = models.TextField(blank=True, null=True)
    delete_status = models.BooleanField(default=False)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def __str__(self):
        return f"Payment ₹{self.amount} - {self.customer.customer_name} ({self.payment_date})"

    class Meta:
        ordering = ['-payment_date']

class ExpenseCategory(models.Model):
    expense_name = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    delete_status = models.BooleanField(default=False)
    
    def __str__(self):
        return self.expense_name or f"Category {self.pk}"  # Fallback if name is blank

class Expense(models.Model):
    expense = models.ForeignKey(ExpenseCategory,on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=3,default='0.000')
    payment_mode = models.CharField(
        max_length=20,
        choices=(('cash', 'Cash'), ('upi', 'UPI'), ('online', 'Online'), ('cheque', 'Cheque')),
        default='cash'
    )
    payment_date = models.DateField()
    description = models.TextField(blank=True, null=True)
    staff = models.ForeignKey(Employe, on_delete=models.PROTECT, null=True, blank=True)
    delete_status = models.BooleanField(default=False)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)

class YieldPercentage(models.Model):
    item = models.ForeignKey(Item,on_delete=models.CASCADE)
    yeild_percentage = models.DecimalField(max_digits=12, decimal_places=3,default='0.000')
    multipler = models.DecimalField(max_digits=12, decimal_places=3,default='0.000')


class DailystockUpdate(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    date = models.DateField()
    opening_stock = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    purchase_stock = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    total_stock = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    todays_sales = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    live_weight_derived = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    closing_stock = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)  # ← Manual
    live_weight_closing = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('item', 'date', 'branch')  # One record per item per day per branch
        ordering = ['-date', 'item__name']

    def __str__(self):
        return f"{self.item.name} - {self.date}"