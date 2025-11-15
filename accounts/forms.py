from django import forms
from .models import CustomUser,Branch, Purchase, PurchaseDetail, Supplier, ItemCategory, Item, RetailSales, RetailSalesDetails, Customer, WholesaleSales, WholesaleSalesDetails,Supplierpay,Employe,Attendance
from django.forms import modelformset_factory
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError


class EmployeeLoginForm(forms.ModelForm):
    employee = forms.ModelChoiceField(
        queryset=Employe.objects.filter(delete_status=False),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Employee Name"
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        max_length=150
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
        max_length=128
    )

    class Meta:
        model = CustomUser
        fields = ['employee', 'username', 'password']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].label_from_instance = lambda obj: f"{obj.name} - {obj.role} ({obj.branch.branch_name if obj.branch else 'No Branch'})"

    def clean_username(self):
        username = self.cleaned_data['username']
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])

        emp = self.cleaned_data['employee']
        user.role = emp.role
        user.branch = emp.branch  # THIS LINE WAS MISSING

        if commit:
            user.save()
        return user

class SupplierForm(forms.ModelForm):
    supplier_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Supplier Name', 'required': 'true', 'autocomplete': 'off'})
    )
    company_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company', 'required': 'true', 'autocomplete': 'off'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email', 'required': 'false', 'autocomplete': 'off'})
    )
    phone_no = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Number', 'required': 'true', 'autocomplete': 'off'})
    )
    address = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address', 'required': 'true', 'autocomplete': 'off'})
    )
    gstin = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'GST Number', 'required': 'true', 'autocomplete': 'off'})
    )

    class Meta:
        model = Supplier
        fields = ['supplier_name', 'company_name', 'email', 'phone_no', 'address', 'gstin']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        qs = Supplier.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_phone_no(self):
        phone_no = self.cleaned_data.get('phone_no')
        if not phone_no.isdigit():
            raise forms.ValidationError("Contact number must contain only digits.")
        if len(phone_no) != 10:
            raise forms.ValidationError("Contact number must be exactly 10 digits.")
        qs = Supplier.objects.filter(phone_no=phone_no)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This contact number is already registered.")
        return phone_no
    
class SupplierpayForm(forms.ModelForm):
    
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        required=True
    )
    payment_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'autocomplete': 'off'}),
        required=True
    )
    amount = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        required=True
    )
    payment_mode = forms.ChoiceField(
        choices=(('cash', 'Cash'), ('online', 'Online')),
        widget=forms.Select(attrs={'class': 'form-control', 'autocomplete': 'off'})
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Description (optional)',
            'rows': 3
        })
    )

    class Meta:
        model = Supplierpay
        fields = ['supplier', 'payment_date', 'amount', 'payment_mode', 'description']


class BranchForm(forms.ModelForm):
    branch_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Branch Name', 'required': 'true', 'autocomplete': 'off'})
    )
    alias = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Initials', 'required': 'true', 'autocomplete': 'off'}),
        label='Initials'
    )
    branch_address = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Branch Address', 'required': 'true', 'autocomplete': 'off'})
    )

    class Meta:
        model = Branch
        fields = ['branch_name','alias','branch_address']

class ItemCategoryForm(forms.ModelForm):
    category_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Category Name',
            'required': 'true',
            'autocomplete': 'off'
        })
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Description (optional)',
            'rows': 3
        })
    )
    is_weight_based = forms.ChoiceField(
        choices=[(True, 'Weight Based (Kg)'), (False, 'Quantity Based')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = ItemCategory
        fields = ['category_name', 'description', 'is_weight_based']

class ItemForm(forms.ModelForm):
    name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Item Name',
            'required': 'true',
            'autocomplete': 'off'
        })
    )
    code = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Item Code',
            'required': 'true',
            'autocomplete': 'off'
        })
    )
    category = forms.ModelChoiceField(
        queryset=ItemCategory.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    price_per_unit_retail = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Price per Unit',
            'required': 'true',
            'step': '0.01'
        })
    )
    price_per_unit_wholesale = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Price per Unit',
            'required': 'true',
            'step': '0.01'
        })
    )
    unit = forms.ChoiceField(
        choices=[
            ('kg', 'Kilogram'),
            ('gm', 'Gram'),
            ('pcs', 'Pieces'),
            ('pkt', 'Packet'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    stock = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Current Stock',
            'step': '0.01'
        })
    )

    class Meta:
        model = Item
        fields = ['name', 'code', 'category', 'price_per_unit_retail', 'price_per_unit_wholesale', 'unit', 'stock']

class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['invoice_number', 'purchase_date', 'supplier', 'branch', 'tax_amount', 'grand_total']

    invoice_number = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'})
    )
    purchase_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'autocomplete': 'off'})
    )
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control', 'autocomplete': 'off'})
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        required=True
    )
    tax_amount = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': True, 'autocomplete': 'off'}),
        required=False
    )
    grand_total = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': True, 'autocomplete': 'off'}),
        required=False
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user and user.role == 'staff' and user.branch:
            self.fields['branch'].initial = user.branch
            self.fields['branch'].widget = forms.HiddenInput()

    def clean_branch(self):
        branch = self.cleaned_data.get('branch')
        if not branch:
            raise ValidationError("Branch selection is required.")
        return branch

class PurchaseDetailForm(forms.ModelForm):
    class Meta:
        model = PurchaseDetail
        fields = ['purchase_type', 'category', 'item', 'tax_percentage', 'purchase_price', 
                  'qty', 'gross_weight', 'empty_weight', 'net_weight', 'total_amount']

    purchase_type = forms.ChoiceField(
        choices=[('retail', 'Retail'), ('wholesale', 'Wholesale')],
        widget=forms.Select(attrs={'class': 'form-control', 'style': 'width: fit-content;', 'required': 'true', 'autocomplete': 'off'})
    )
    category = forms.ModelChoiceField(
        queryset=ItemCategory.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control category-select', 'style': 'width: fit-content;', 'required': 'true', 'autocomplete': 'off'})
    )
    item = forms.ModelChoiceField(
        queryset=Item.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control item-select', 'style': 'width: fit-content;', 'required': 'true', 'autocomplete': 'off'})
    )
    tax_percentage = forms.ChoiceField(
        choices=[('0', '0%'), ('12', '12%'), ('18', '18%')],
        widget=forms.Select(attrs={'class': 'form-control', 'style': 'width: fit-content;', 'autocomplete': 'off'}),
        initial='0'
    )
    purchase_price = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control', 'required': 'true', 'autocomplete': 'off'}))
    qty = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off'}))
    gross_weight = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off'}))
    empty_weight = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off'}))
    net_weight = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off'}))
    total_amount = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control', 'required': 'true', 'readonly': 'true', 'autocomplete': 'off'}))
    is_weight_based = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.prefix and f'{self.prefix}-category' in self.data:
            try:
                category_id = int(self.data.get(f'{self.prefix}-category'))
                self.fields['item'].queryset = Item.objects.filter(category_id=category_id)
                category = ItemCategory.objects.get(category_id=category_id)
                self.initial['is_weight_based'] = str(category.is_weight_based).lower()
            except (ValueError, TypeError, ItemCategory.DoesNotExist):
                self.fields['item'].queryset = Item.objects.none()
                self.initial['is_weight_based'] = 'false'
        elif self.instance.pk and self.instance.category:
            self.fields['item'].queryset = Item.objects.filter(category=self.instance.category)
            self.initial['is_weight_based'] = str(self.instance.category.is_weight_based).lower()
        else:
            self.fields['item'].queryset = Item.objects.none()
            self.initial['is_weight_based'] = 'false'

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        cleaned_data['is_weight_based'] = str(category.is_weight_based).lower() if category else 'false'
        return cleaned_data

PurchaseDetailFormSet = inlineformset_factory(
    Purchase, PurchaseDetail, form=PurchaseDetailForm, extra=1, can_delete=True
)

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['customer_name', 'customer_phone', 'customer_address', 'gstin']

    customer_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Customer Name', 'autocomplete': 'off'})
    )
    customer_phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number', 'autocomplete': 'off'})
    )
    customer_address = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address', 'autocomplete': 'off'})
    )
    gstin = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'GSTIN', 'autocomplete': 'off'})
    )

    def __init__(self, *args, customer_id=None, **kwargs):
        self.customer_id = customer_id
        super().__init__(*args, **kwargs)

    def clean_customer_phone(self):
        phone = self.cleaned_data.get('customer_phone', '').strip()
        if phone:
            if not phone.isdigit():
                raise forms.ValidationError("Phone number must contain only digits.")
            if len(phone) != 10:
                raise forms.ValidationError("Phone number must be exactly 10 digits.")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        phone = cleaned_data.get('customer_phone', '').strip()
        gstin = cleaned_data.get('gstin', '').strip()

        # ONLY validate uniqueness if creating new (no customer_id)
        if not self.customer_id:
            if phone and Customer.objects.filter(customer_phone=phone).exists():
                self.add_error('customer_phone', "A customer with this phone number already exists.")
            if gstin and Customer.objects.filter(gstin=gstin).exists():
                self.add_error('gstin', "A customer with this GSTIN already exists.")
        return cleaned_data

class RetailSalesForm(forms.ModelForm):
    class Meta:
        model = RetailSales
        fields = ['receipt_no', 'sales_date', 'branch', 'tax_amount', 'grand_total', 'payment_mode','take_amay_employee']

    receipt_no = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': True, 'autocomplete': 'off'})
    )
    sales_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'autocomplete': 'off'})
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        required=True
    )
    tax_amount = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': True, 'autocomplete': 'off'}),
        required=False
    )
    grand_total = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': True, 'autocomplete': 'off'}),
        required=False
    )
    payment_mode = forms.ChoiceField(
        choices=(('cash', 'Cash'), ('online', 'Online'), ('pending', 'Pending')),
        widget=forms.Select(attrs={'class': 'form-control', 'autocomplete': 'off'})
    )
    take_amay_employee = forms.ModelChoiceField(
        queryset=Employe.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        required=False,
        label="Take Away"
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user and user.role == 'staff' and user.branch:
            self.fields['branch'].initial = user.branch
            self.fields['branch'].widget = forms.HiddenInput()

    def clean_branch(self):
        branch = self.cleaned_data.get('branch')
        if not branch:
            raise ValidationError("Branch selection is required.")
        return branch

class RetailSalesDetailForm(forms.ModelForm):
    class Meta:
        model = RetailSalesDetails
        fields = ['item', 'tax_percentage', 'price_per_unit', 'qty', 'net_weight', 'token', 'total_amount']

    item = forms.ModelChoiceField(
        queryset=Item.objects.all(),
        widget=forms.HiddenInput()
    )
    tax_percentage = forms.ChoiceField(
        choices=[('0', '0%'), ('12', '12%'), ('18', '18%')],
        widget=forms.Select(attrs={'class': 'form-control', 'style': 'width: fit-content;'}),
        initial='0'
    )
    price_per_unit = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': True, 'autocomplete': 'off'})
    )
    qty = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off'})
    )
    net_weight = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off'})
    )
    token = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        required=False
    )
    total_amount = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': True, 'autocomplete': 'off'})
    )

RetailSalesDetailFormSet = modelformset_factory(
    RetailSalesDetails, form=RetailSalesDetailForm, extra=1, can_delete=True
)

class WholesaleSalesForm(forms.ModelForm):
    class Meta:
        model = WholesaleSales
        fields = ['receipt_no', 'sales_date', 'branch', 'tax_amount', 'grand_total', 'payment_mode', 'paid_amount']

    receipt_no = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        required=True
    )
    sales_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'autocomplete': 'off'})
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        required=True
    )
    tax_amount = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': True, 'autocomplete': 'off'}),
        required=False
    )
    grand_total = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': True, 'autocomplete': 'off'}),
        required=False
    )
    payment_mode = forms.ChoiceField(
        choices=(('pending', 'Pending'), ('cash', 'Cash'), ('online', 'Online')),
        widget=forms.Select(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        initial='pending'
    )
    paid_amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        required=True
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user and user.role == 'staff' and user.branch:
            self.fields['branch'].initial = user.branch
            self.fields['branch'].widget = forms.HiddenInput()

    def clean_branch(self):
        branch = self.cleaned_data.get('branch')
        if not branch:
            raise ValidationError("Branch selection is required.")
        return branch

    def clean(self):
        cleaned_data = super().clean()
        paid_amount = cleaned_data.get('paid_amount')
        grand_total = cleaned_data.get('grand_total')
        if paid_amount and grand_total and paid_amount > grand_total:
            raise ValidationError("Paid amount cannot be greater than the grand total.")
        return cleaned_data

class WholesaleSalesDetailForm(forms.ModelForm):
    class Meta:
        model = WholesaleSalesDetails
        fields = ['item', 'tax_percentage', 'price_per_unit', 'qty', 'net_weight', 'token', 'total_amount']

    item = forms.ModelChoiceField(
        queryset=Item.objects.all(),
        widget=forms.HiddenInput()
    )
    tax_percentage = forms.ChoiceField(
        choices=[('0', '0%'), ('12', '12%'), ('18', '18%')],
        widget=forms.Select(attrs={'class': 'form-control', 'style': 'width: fit-content;'}),
        initial='0'
    )
    price_per_unit = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': True, 'autocomplete': 'off'})
    )
    qty = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off'})
    )
    net_weight = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off'})
    )
    token = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        required=False,
        max_length=50
    )
    total_amount = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': True, 'autocomplete': 'off'})
    )

WholesaleSalesDetailFormSet = modelformset_factory(
    WholesaleSalesDetails, form=WholesaleSalesDetailForm, extra=1, can_delete=True
)

class EmployeForm(forms.ModelForm):
    class Meta:
        model = Employe
        fields = ['emp_id', 'name', 'phone_no', 'address', 'role', 'branch', 'salary_per_day']

    emp_id = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Employee ID',
            'autocomplete': 'off'
        })
    )
    name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Employee Name',
            'autocomplete': 'off'
        })
    )
    phone_no = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone Number',
            'autocomplete': 'off'
        })
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Address (optional)',
            'rows': 3,
            'autocomplete': 'off'
        })
    )
    role = forms.ChoiceField(
        choices=Employe.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,  # Optional if staff can be without branch
        empty_label="--- Select Branch ---"
    )
    salary_per_day = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control','autocomplete': 'off'}),
        required=True
    )

    def clean_phone_no(self):
        phone = self.cleaned_data.get('phone_no')
        if phone:
            if not phone.isdigit():
                raise forms.ValidationError("Phone number must contain only digits.")
            if len(phone) != 10:
                raise forms.ValidationError("Phone number must be exactly 10 digits.")
            # Check uniqueness
            if Employe.objects.filter(phone_no=phone).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("An employee with this phone number already exists.")
        return phone

    def clean_emp_id(self):
        emp_id = self.cleaned_data.get('emp_id')
        if Employe.objects.filter(emp_id=emp_id).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This Employee ID is already taken.")
        return emp_id
    

class AttendanceInlineForm(forms.ModelForm):
    status = forms.ChoiceField(
        choices=Attendance.ATTENDANCE_CHOICES,
        widget=forms.RadioSelect,
        required=True,
        initial='present'
    )

    class Meta:
        model = Attendance
        fields = ['status']

    def clean_status(self):
        status = self.cleaned_data.get('status')
        # If not in POST, use initial
        if not status and self.initial.get('status'):
            return self.initial['status']
        return status
