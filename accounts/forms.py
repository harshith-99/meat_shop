from django import forms
from .models import DailystockUpdate,YieldPercentage,ExpenseCategory,Expense,CustomUser,Branch, Purchase, PurchaseDetail, Supplier, ItemCategory, Item, RetailSales, RetailSalesDetails, Customer, WholesaleSales, WholesaleSalesDetails,Supplierpay,Employe,Attendance,WholesalePayment
from django.forms import modelformset_factory
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from decimal import Decimal

class DailyStockUpdateForm(forms.ModelForm):
    class Meta:
        model = DailystockUpdate
        fields = [
            'item', 'opening_stock', 'purchase_stock', 'total_stock',
            'todays_sales', 'live_weight_derived', 'closing_stock', 'live_weight_closing'
        ]
        widgets = {
            'item': forms.HiddenInput(),
            'opening_stock': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'purchase_stock': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'total_stock': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'todays_sales': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'live_weight_derived': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'closing_stock': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'live_weight_closing': forms.NumberInput(attrs={
                'class': 'form-control live-closing',
                'readonly': 'readonly'
            }),
        }

class YieldPercentageForm(forms.ModelForm):
    item = forms.ModelChoiceField(
        queryset=Item.objects.all().select_related('category').order_by(
            'category__category_name', 'name'   # First by category, then by item name
        ),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    yeild_percentage = forms.DecimalField(
        widget = forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off', 'step': '0.01'})
    )
    multipler = forms.DecimalField(
        widget = forms.NumberInput(attrs = {'class' :'form-control','autocomplete': 'off', 'step': '0.01'})
    )
    class Meta:
        model = YieldPercentage
        fields = ['item','yeild_percentage','multipler']

class ExpenseCategoryForm(forms.ModelForm):
    expense_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Expense Name'}),
        max_length=150
    )
    description = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Description'}),
    )
    class Meta:
        model = ExpenseCategory
        fields = ['expense_name', 'description']

class ExpenseForm(forms.ModelForm):
    expense = forms.ModelChoiceField(
        queryset=ExpenseCategory.objects.filter(delete_status=False),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
        label="Expense Category"
    )
    amount = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off', 'step': '0.01'}),
        required=True,
        min_value=Decimal('0.01')
    )
    payment_mode = forms.ChoiceField(
        choices=(('cash', 'Cash'), ('upi', 'UPI'), ('online', 'Online'), ('cheque', 'Cheque')),
        widget=forms.Select(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        required=True
    )
    payment_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'autocomplete': 'off'}),
        required=True
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Description (optional)',
            'rows': 3,
            'autocomplete': 'off'
        })
    )
    staff = forms.ModelChoiceField(
        queryset=Employe.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        required=False,
        label="Select Staff",
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        widget=forms.HiddenInput(),  # Default: hidden
        required=False
    )

    class Meta:
        model = Expense
        fields = ['expense', 'amount', 'payment_mode', 'payment_date', 'description', 'staff', 'branch']

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Set queryset for branch
        self.fields['branch'].queryset = Branch.objects.all()

        # Non-admin (staff/manager): auto-set branch from login
        if user and user.role in ['staff', 'manager'] and user.branch:
            self.fields['branch'].initial = user.branch
            self.fields['branch'].widget = forms.HiddenInput()

            # Force value on validation error
            if self.data:
                mutable_data = self.data.copy()
                mutable_data['branch'] = str(user.branch.pk)
                self.data = mutable_data

        # Admin/Super Admin: show dropdown
        elif user and user.role in ['admin', 'super_admin']:
            self.fields['branch'].widget = forms.Select(attrs={'class': 'form-control'})
            self.fields['branch'].required = True
            self.fields['branch'].empty_label = "-- Select Branch --"
            self.fields['branch'].queryset = Branch.objects.all().order_by('branch_name')
        else:
            self.fields['branch'].widget = forms.HiddenInput()

    
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
        user.branch = emp.branch

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
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email', 'autocomplete': 'off'})
    )
    phone_no = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Number', 'required': 'true', 'autocomplete': 'off'})
    )
    address = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address', 'required': 'true', 'autocomplete': 'off'})
    )
    gstin = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'GST Number', 'autocomplete': 'off'})
    )

    class Meta:
        model = Supplier
        fields = ['supplier_name', 'company_name', 'email', 'phone_no', 'address', 'gstin']

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
        required=True,
        to_field_name='supplier_id',
    )
    payment_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'autocomplete': 'off'}),
        required=True
    )
    amount = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off', 'step': '0.01'}),
        required=True,
        min_value=Decimal('0.01')
    )
    payment_mode = forms.ChoiceField(
        choices=(('cash', 'Cash'), ('online', 'Online'), ('cheque', 'Cheque'), ('upi', 'UPI')),
        widget=forms.Select(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        required=True
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Description (optional)',
            'rows': 3,
            'autocomplete': 'off'
        })
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        widget=forms.HiddenInput(),  # Will be auto-set
        required=False
    )

    class Meta:
        model = Supplierpay
        fields = ['supplier', 'payment_date', 'amount', 'payment_mode', 'description', 'branch']

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        self.fields['branch'].queryset = Branch.objects.all()

        # Auto-fill & restrict branch for non-admin users
        if user and user.role in ['staff', 'manager'] and user.branch:
            self.fields['branch'].initial = user.branch
            self.fields['branch'].widget = forms.HiddenInput()

            # Force branch value even on validation error
            if self.data:
                mutable_data = self.data.copy()
                mutable_data[f'{self.prefix}-branch' if self.prefix else 'branch'] = str(user.branch.pk)
                self.data = mutable_data

        # Admin can choose any branch
        elif user and user.role in ['admin', 'super_admin']:
            self.fields['branch'].widget = forms.Select(attrs={'class': 'form-control'})
            self.fields['branch'].queryset = Branch.objects.all().order_by('branch_name')
            self.fields['branch'].required = True
            self.fields['branch'].empty_label = "-- Select Branch --"
        else:
            self.fields['branch'].widget = forms.HiddenInput()

        # Optional: Restrict suppliers to those who supplied to user's branch (for staff/manager)
        if user and user.role in ['staff', 'manager'] and user.branch:
            allowed_suppliers = Purchase.objects.filter(
                branch=user.branch,
                delete_status=False
            ).values_list('supplier_id', flat=True).distinct()
            self.fields['supplier'].queryset = Supplier.objects.filter(supplier_id__in=allowed_suppliers)
        else:
            self.fields['supplier'].queryset = Supplier.objects.all()


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
            ('num', 'Number'),
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

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # if user and user.role == 'manager':
        #     readonly_fields = ['name', 'code', 'category', 'unit', 'stock']
        #     for field_name in readonly_fields:
        #         self.fields[field_name].widget.attrs['readonly'] = True
        #         self.fields[field_name].disabled = True

        #     self.fields['price_per_unit_retail'].widget.attrs.update({
        #         'class': 'form-control border-success',
        #         'placeholder': 'Retail Price (Editable by Manager)'
        #     })
        #     self.fields['price_per_unit_wholesale'].widget.attrs.update({
        #         'class': 'form-control border-success',
        #         'placeholder': 'Wholesale Price (Editable by Manager)'
        #     })

        # Everyone EXCEPT super_admin: Stock is readonly
        # Only super_admin can edit stock
        if user and user.role != 'super_admin':
            self.fields['stock'].widget.attrs['readonly'] = True
            self.fields['stock'].widget.attrs['class'] += ' bg-light'
            # self.fields['stock'].help_text = "Only super admin can update stock."

        # Super Admin: Full access (no restrictions)

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not code:
            raise ValidationError("Item code is required.")

        code = code.strip()

        # Normalize: uppercase + remove leading zeros after letters
        import re
        match = re.match(r'([A-Za-z]+)(0*)(\d*)', code.upper())
        if match:
            prefix = match.group(1)
            number = match.group(3) or '0'  # if no digits, treat as 0
            normalized = prefix + number
        else:
            # No number part (e.g., "ABC")
            normalized = code.upper()

        # Search for any existing code that normalizes to the same
        existing_items = Item.objects.exclude(pk=self.instance.pk if self.instance.pk else 0)
        
        for item in existing_items:
            existing_code = item.code.upper()
            existing_match = re.match(r'([A-Za-z]+)(0*)(\d*)', existing_code)
            if existing_match:
                existing_prefix = existing_match.group(1)
                existing_number = existing_match.group(3) or '0'
                existing_normalized = existing_prefix + existing_number
            else:
                existing_normalized = existing_code

            if normalized == existing_normalized:
                raise ValidationError(
                    f"Item code '{code}' is already in use. "
                    "Codes like b1, B01, b001 are considered the same."
                )

        return code
    
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

        if user and user.role in ['staff', 'manager'] and user.branch:
            # 1. Set initial value
            self.initial['branch'] = user.branch.branch_id  # ← Use .id, not object

            # 2. Make it hidden
            self.fields['branch'].widget = forms.HiddenInput()

            # 3. CRITICAL: Force the value into POST data on validation error
            if self.data:
                # Make self.data mutable
                mutable_data = self.data.copy()
                mutable_data['branch'] = str(user.branch.branch_id)
                self.data = mutable_data

    def clean_branch(self):
        branch = self.cleaned_data.get('branch')
        if not branch:
            raise ValidationError("Branch selection is required.")
        return branch

class PurchaseDetailForm(forms.ModelForm):
    class Meta:
        model = PurchaseDetail
        fields = ['purchase_type', 'category', 'item', 'tax_percentage', 'purchase_price', 
                  'qty', 'no_of_boxes','gross_weight', 'empty_weight', 'net_weight', 'total_amount']

    purchase_type = forms.ChoiceField(
        choices=[('retail', 'Retail'), ('wholesale', 'Wholesale')],
        widget=forms.Select(attrs={'class': 'form-control', 'style': 'width: 85px;', 'required': 'true', 'autocomplete': 'off'}),
        initial='retail'
    )
    category = forms.ModelChoiceField(
        queryset=ItemCategory.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control category-select', 'style': 'width: 93px;', 'required': 'true', 'autocomplete': 'off'})
    )
    item = forms.ModelChoiceField(
        queryset=Item.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control item-select', 'style': 'width: 93px;', 'required': 'true', 'autocomplete': 'off'})
    )
    tax_percentage = forms.ChoiceField(
        choices=[('0', '0%'), ('12', '12%'), ('18', '18%')],
        widget=forms.Select(attrs={'class': 'form-control', 'style': 'width: 40px;', 'autocomplete': 'off'}),
        initial='0',
        required=False
    )

    purchase_price = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control', 'required': 'true', 'style': 'width: 68px;','autocomplete': 'off'}))
    qty = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control', 'style': 'width: 68px;','autocomplete': 'off'}))
    no_of_boxes = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control', 'style': 'width: 68px;','autocomplete': 'off'}),required=False)
    gross_weight = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control', 'style': 'width: 85px;','autocomplete': 'off'}))
    empty_weight = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control', 'style': 'width: 85px;','autocomplete': 'off'}))
    net_weight = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control', 'style': 'width: 85px;','autocomplete': 'off'}))
    total_amount = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control', 'style': 'width: 85px;','required': 'true', 'readonly': 'true', 'autocomplete': 'off'}))
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
    whole_sale = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Customer
        fields = ['customer_name', 'customer_phone', 'customer_address', 'gstin', 'whole_sale']

    customer_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Customer Name',
            'autocomplete': 'off'
        }),
        required=False
    )
    customer_phone = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone Number (10 digits)',
            'autocomplete': 'off'
        }),
        required=False
    )
    customer_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Address'
        }),
        required=False
    )
    gstin = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'GSTIN (optional)'
        }),
        required=False  # Important: allow blank
    )

    def clean_customer_phone(self):
        phone = self.cleaned_data.get('customer_phone', '').strip()
        if phone:
            if not phone.isdigit():
                raise ValidationError("Phone number must contain only digits.")
            if len(phone) != 10:
                raise ValidationError("Phone number must be exactly 10 digits.")
            if Customer.objects.filter(customer_phone=phone).exclude(pk=self.instance.pk).exists():
                raise ValidationError("This phone number is already registered.")
        return phone

    def clean_gstin(self):
        gstin = self.cleaned_data.get('gstin', '').strip().upper()

        # If GSTIN is empty or None → allow it (no uniqueness check)
        if not gstin:
            return gstin

        # Only check uniqueness if GSTIN is provided
        if Customer.objects.filter(gstin__iexact=gstin).exclude(pk=self.instance.pk).exists():
            raise ValidationError("This GSTIN is already registered.")

        return gstin


# === FINAL CustomerForm — NO MORE ERRORS! ===
class CustomerDataForm(forms.Form):
    customer_name = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Customer Name',
            'autocomplete': 'off'
        })
    )
    customer_phone = forms.CharField(
        required=False,
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone Number',
            'autocomplete': 'off'
        })
    )
    customer_address = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Address',
            'autocomplete': 'off'
        })
    )
    gstin = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'GSTIN',
            'autocomplete': 'off'
        })
    )

    def __init__(self, *args, require_customer=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.require_customer = require_customer
        if require_customer:
            self.fields['customer_name'].required = True
            self.fields['customer_phone'].required = True
            self.fields['customer_address'].required = True

    def clean_customer_phone(self):
        phone = self.cleaned_data.get('customer_phone', '').strip()
        if phone:
            if not phone.isdigit():
                raise ValidationError("Phone number must contain only digits.")
            if len(phone) != 10:
                raise ValidationError("Phone number must be exactly 10 digits.")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        if self.require_customer:
            name = cleaned_data.get('customer_name', '').strip()
            phone = cleaned_data.get('customer_phone', '').strip()
            address = cleaned_data.get('customer_address', '').strip()
            if not (name and phone and address):
                raise ValidationError("All customer fields are required for Take-Away.")
        return cleaned_data

class RetailSalesForm(forms.ModelForm):
    class Meta:
        model = RetailSales
        fields = ['receipt_no', 'sales_date', 'branch', 'tax_amount','discount','total', 'grand_total', 'payment_mode','take_amay_employee']

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
    discount = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': False, 'autocomplete': 'off'}),
        required=False
    )
    total = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': True, 'autocomplete': 'off'}),
        required=False
    )
    grand_total = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': True, 'autocomplete': 'off'}),
        required=False
    )
    payment_mode = forms.ChoiceField(
        choices=(('cash', 'Cash'), ('upi', 'UPI'),('cheque', 'Cheque'),('online', 'Online'), ('pending', 'Pending')),
        widget=forms.Select(attrs={'class': 'form-control', 'autocomplete': 'off'})
    )
    take_amay_employee = forms.ModelChoiceField(
        queryset=Employe.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        required=False,
        label="Take Away",
        empty_label="Store Customer"
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        if user and user.role in ['staff', 'manager'] and user.branch:
            branch_pk = user.branch.pk
            self.initial['branch'] = branch_pk
            self.fields['branch'].queryset = Branch.objects.filter(pk=branch_pk)
            self.fields['branch'].widget = forms.HiddenInput()

            if self.data:  # We are in POST
                self.data = self.data.copy()  # Make mutable
                self.data['branch'] = str(branch_pk)  # Must be string!

            if self.instance.pk and not self.instance.branch_id:
                self.instance.branch_id = branch_pk

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
        fields = ['receipt_no', 'sales_date', 'branch', 'tax_amount','discount','total', 'grand_total', 'payment_mode', 'paid_amount']

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
    discount = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': False, 'autocomplete': 'off'}),
        required=False
    )
    total = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': True, 'autocomplete': 'off'}),
        required=False
    )
    grand_total = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': True, 'autocomplete': 'off'}),
        required=False
    )
    payment_mode = forms.ChoiceField(
        choices=(('credit', 'Credit'), ('cash', 'Cash'),('upi', 'UPI'),('cheque', 'Cheque'), ('online', 'Online')),
        widget=forms.Select(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        initial='credit'
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

        if user and user.role in ['staff', 'manager'] and user.branch:
            branch_pk = user.branch.pk

            # 1. Set initial + restrict queryset
            self.initial['branch'] = branch_pk
            self.fields['branch'].queryset = Branch.objects.filter(pk=branch_pk)

            # 2. Make it hidden
            self.fields['branch'].widget = forms.HiddenInput()

            # 3. CRITICAL: Force the value into POST data so Django sees it
            if self.data:  # We are in POST
                self.data = self.data.copy()  # Make mutable
                self.data['branch'] = str(branch_pk)  # Must be string!

            # Optional: Also set on instance if editing (rare case)
            if self.instance.pk and not self.instance.branch_id:
                self.instance.branch_id = branch_pk

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
        widget=forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off'})
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
    
class WholesalePaymentForm(forms.ModelForm):
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.filter(whole_sale=True, delete_status=False),
        widget=forms.Select(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        required=True,
        empty_label="-- Select Wholesale Customer --"
    )
    payment_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
    )
    amount = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        required=True,
        min_value=Decimal('0.01')
    )
    payment_mode = forms.ChoiceField(
        choices=(('cash', 'Cash'), ('upi', 'UPI'), ('online', 'Online'), ('cheque', 'Cheque')),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Description (optional)',
            'rows': 3
        })
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        widget=forms.HiddenInput(),
        required=False
    )

    class Meta:
        model = WholesalePayment
        fields = ['customer', 'payment_date', 'amount', 'payment_mode', 'description', 'branch']

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Set queryset for branch
        self.fields['branch'].queryset = Branch.objects.all()

        # Non-admin: auto-set branch
        if user and user.role in ['staff', 'manager'] and user.branch:
            self.fields['branch'].initial = user.branch
            self.fields['branch'].widget = forms.HiddenInput()

            if self.data:
                mutable_data = self.data.copy()
                mutable_data[f'{self.prefix}-branch' if self.prefix else 'branch'] = str(user.branch.pk)
                self.data = mutable_data

        # Admin: show dropdown
        elif user and user.role in ['admin', 'super_admin']:
            self.fields['branch'].widget = forms.Select(attrs={'class': 'form-control'})
            self.fields['branch'].required = True
            self.fields['branch'].queryset = Branch.objects.all().order_by('branch_name')
            self.fields['branch'].empty_label = "-- Select Branch --"
