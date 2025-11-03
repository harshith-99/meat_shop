from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, F, Q
from django.contrib import messages
from django.forms import modelformset_factory
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from decimal import Decimal, InvalidOperation
from .forms import PurchaseForm, PurchaseDetailFormSet, ItemCategoryForm, BranchForm, SupplierForm, ItemForm, RetailSalesForm, RetailSalesDetailFormSet, CustomerForm, WholesaleSalesForm, WholesaleSalesDetailFormSet,SupplierpayForm
from .models import Purchase, PurchaseDetail, Branch, Supplier, ItemCategory, Item, RetailSales, RetailSalesDetails, Customer, WholesaleSales, WholesaleSalesDetails,Supplierpay
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.http import HttpRequest
from datetime import datetime, date

logger = logging.getLogger(__name__)

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    return render(request, 'accounts/login.html', {'form': form})

def user_logout(request):
    request.session.flush()
    logout(request)
    return redirect('login')

@require_GET
def items_by_category(request: HttpRequest, category_id: int):
    print(f"Fetching items for category_id: {category_id}")
    items = Item.objects.filter(category_id=category_id).values('id', 'name')
    if not items.exists():
        print("No items found for this category")
    return JsonResponse(list(items), safe=False)

@login_required(login_url='login')
def dashboard_view(request):
    user = request.user
    branch_name = None
    if hasattr(user, "branch") and user.branch:
        branch_name = user.branch.branch_name
    context = {
        "user": user,
        "branch_name": branch_name,
    }
    return render(request, "dashboard.html", context)

@login_required(login_url='login')
def supplier_list(request):
    suppliers = Supplier.objects.all()
    return render(request, "supplier_list.html", {"suppliers": suppliers})

@login_required(login_url='login')
def supplier_add(request):
    if request.method == "POST":
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("supplier_list")
    else:
        form = SupplierForm()
    return render(request, "supplier_add.html", {"form": form})

@login_required
def supplier_pay(request):
    if request.method == "POST":
        form = SupplierpayForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Payment recorded successfully!")
            return redirect("supplier_pay")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SupplierpayForm()

    return render(request, "supplier_pay.html", {"form": form})

@login_required
def supplier_payment_list(request):
    is_manager = request.user.role in ['manager', 'admin', 'super_admin']

    supplier_id = request.GET.get('supplier')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    payments = Supplierpay.objects.filter(delete_status=False)

    if supplier_id:
        payments = payments.filter(supplier_id=supplier_id)  # OK: FK on Supplierpay

    if from_date:
        try:
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
            payments = payments.filter(payment_date__gte=from_date)
        except ValueError:
            pass

    if to_date:
        try:
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
            payments = payments.filter(payment_date__lte=to_date)
        except ValueError:
            pass

    payments = payments.select_related('supplier').order_by('-payment_date')

    # --- CORRECTED: Use 'supplier_id' instead of 'id' ---
    supplier_stats = Supplier.objects.annotate(
        total_purchase=Sum(
            'purchase__details__total_amount',
            filter=Q(purchase__delete_status=False)
        ),
        total_paid=Sum(
            'supplierpay__amount',
            filter=Q(supplierpay__delete_status=False)
        )
    ).annotate(
        balance=F('total_purchase') - F('total_paid')
    ).values(
        'supplier_id', 'supplier_name',  # Changed 'id' → 'supplier_id'
        'total_purchase', 'total_paid', 'balance'
    )

    if supplier_id:
        supplier_stats = supplier_stats.filter(supplier_id=supplier_id)  # Use supplier_id

    context = {
        'payments': payments,
        'suppliers': Supplier.objects.all(),
        'selected_supplier': supplier_id,
        'from_date': request.GET.get('from_date'),  # Keep as string
        'to_date': request.GET.get('to_date'),
        'supplier_stats': list(supplier_stats),
        'is_manager': is_manager,
    }
    return render(request, 'supplier_payment_list.html', context)


@login_required
def supplier_payment_update(request, pk):
    if request.user.role not in ['manager', 'admin', 'super_admin']:
        messages.error(request, "You are not authorized.")
        return redirect('supplier_payment_list')

    payment = get_object_or_404(Supplierpay, pk=pk, delete_status=False)
    if request.method == 'POST':
        form = SupplierpayForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            messages.success(request, "Payment updated successfully.")
            return redirect('supplier_payment_list')
    else:
        form = SupplierpayForm(instance=payment)
    return render(request, 'supplier_payment_form.html', {'form': form, 'payment': payment})


@login_required
def supplier_payment_delete(request, pk):
    if request.user.role not in ['manager', 'admin', 'super_admin']:
        messages.error(request, "You are not authorized.")
        return redirect('supplier_payment_list')

    payment = get_object_or_404(Supplierpay, pk=pk, delete_status=False)
    payment.delete_status = True
    payment.save()
    messages.success(request, "Payment deleted (soft).")
    return redirect('supplier_payment_list')

@login_required
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    supplier.delete()
    messages.success(request, "Supplier deleted successfully.")
    return redirect('supplier_list')

@login_required
def supplier_update(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == "POST":
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, "Supplier updated successfully!")
            return redirect('supplier_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SupplierForm(instance=supplier)
    context = {
        'form': form,
        'supplier': supplier
    }
    return render(request, 'supplier_update.html', context)

@login_required(login_url='login')
def branch_list(request):
    branches = Branch.objects.all()
    return render(request, "branch_list.html", {"branches": branches})

@login_required
def branch_add(request):
    if request.method == "POST":
        form = BranchForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Branch added successfully!")
            return redirect("branch_list")
        else:
            messages.error(request, f"Form errors: {form.errors}")
    else:
        form = BranchForm()
    return render(request, "branch_add.html", {"form": form})

@login_required(login_url='login')
def branch_delete(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    branch.delete()
    messages.success(request, "Branch deleted successfully.")
    return redirect('branch_list')

@login_required
def branch_update(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    if request.method == "POST":
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            messages.success(request, "Branch updated successfully!")
            return redirect('branch_list')
        else:
            messages.error(request, "Please correct the errors.")
    else:
        form = BranchForm(instance=branch)
    context = {
        'form': form,
        'branch': branch
    }
    return render(request, 'branch_update.html', context)

@login_required(login_url='login')
def item_category_list(request):
    categories = ItemCategory.objects.all()
    return render(request, "category_list.html", {"categories": categories})

@require_GET
def category_details(request, category_id):
    try:
        category = ItemCategory.objects.get(category_id=category_id)
        return JsonResponse({'is_weight_based': category.is_weight_based})
    except ItemCategory.DoesNotExist:
        return JsonResponse({'error': 'Category not found', 'is_weight_based': False}, status=404)

@login_required
def item_category_add(request):
    if request.method == "POST":
        form = ItemCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category added successfully!")
            return redirect("category_list")
        else:
            messages.error(request, f"Form errors: {form.errors}")
    else:
        form = ItemCategoryForm()
    return render(request, "category_add.html", {"form": form})

@login_required(login_url='login')
def item_category_delete(request, pk):
    category = get_object_or_404(ItemCategory, pk=pk)
    category.delete()
    messages.success(request, "Category deleted successfully.")
    return redirect('category_list')

@login_required
def item_category_update(request, pk):
    category = get_object_or_404(ItemCategory, pk=pk)
    if request.method == "POST":
        form = ItemCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated successfully!")
            return redirect('category_list')
        else:
            messages.error(request, "Please correct the errors.")
    else:
        form = ItemCategoryForm(instance=category)
    context = {
        'form': form,
        'category': category
    }
    return render(request, 'category_update.html', context)

@login_required
def item_add(request):
    if request.method == "POST":
        form = ItemForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Item added successfully!")
            return redirect("item_list")
        else:
            messages.error(request, f"Form errors: {form.errors}")
    else:
        form = ItemForm()
    return render(request, "item_add.html", {"form": form})

@login_required(login_url='login')
def item_list(request):
    items = Item.objects.all()
    return render(request, "item_list.html", {"items": items})

@login_required
def item_update(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.method == "POST":
        form = ItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Item updated successfully!")
            return redirect('item_list')
        else:
            messages.error(request, "Please correct the errors.")
    else:
        form = ItemForm(instance=item)
    context = {
        'form': form,
        'category': item
    }
    return render(request, 'item_update.html', context)

@login_required(login_url='login')
def item_delete(request, pk):
    item = get_object_or_404(Item, pk=pk)
    item.delete()
    messages.success(request, "Item deleted successfully.")
    return redirect('item_list')

@login_required
def purchase_add(request):
    is_admin_like = request.user.role in ['super_admin', 'admin', 'manager']
    if request.method == "POST":
        form = PurchaseForm(request.POST, user=request.user)
        formset = PurchaseDetailFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            invoice_no = form.cleaned_data['invoice_number']
            if Purchase.objects.filter(invoice_number=invoice_no).exists():
                messages.error(request, f"Invoice number {invoice_no} already exists!")
                return render(request, "purchase_add.html", {
                    'form': form,
                    'formset': formset,
                    'is_admin_like': is_admin_like,
                    'reset_form': False
                })
            with transaction.atomic():
                purchase = form.save(commit=False)
                purchase.added_by = request.user
                if not is_admin_like:
                    purchase.branch = request.user.branch
                purchase.save()
                for detail in formset:
                    if not detail.instance._state.adding and detail.cleaned_data.get('DELETE'):
                        if detail.instance.pk:
                            detail.instance.delete()
                    elif detail.cleaned_data and not detail.cleaned_data.get('DELETE'):
                        detail_instance = detail.save(commit=False)
                        detail_instance.purchase = purchase
                        detail_instance.save()
                        item = detail.cleaned_data['item']
                        if item.category.is_weight_based:
                            item.stock += detail.cleaned_data['net_weight']
                        else:
                            item.stock += detail.cleaned_data['qty']
                        item.save()
                messages.success(request, f"Purchase {invoice_no} saved successfully!")
                return redirect("purchase_add")
        else:
            logger.error("Form validation failed - Form errors: %s, Formset errors: %s", form.errors, [f.errors for f in formset])
            messages.error(request, "Please correct the errors below.")
            return render(request, "purchase_add.html", {
                'form': form,
                'formset': formset,
                'is_admin_like': is_admin_like,
                'reset_form': False
            })
    else:
        initial = {
            'purchase_date': date.today(),
        }
        if not is_admin_like and request.user.branch:
            initial['branch'] = request.user.branch
        form = PurchaseForm(initial=initial, user=request.user)
        formset = PurchaseDetailFormSet(queryset=PurchaseDetail.objects.none())
        return render(request, "purchase_add.html", {
            'form': form,
            'formset': formset,
            'is_admin_like': is_admin_like,
            'reset_form': True
        })

@login_required(login_url='login')
def purchase_list(request):
    is_admin_like = request.user.role in ['super_admin', 'admin']
    if is_admin_like:
        purchases = Purchase.objects.filter(delete_status=False).select_related('supplier', 'branch')
    else:
        purchases = Purchase.objects.filter(branch=request.user.branch, delete_status=False).select_related('supplier')
    
    # Calculate totals for each purchase
    purchase_data = []
    for purchase in purchases:
        details = purchase.details.all()
        total_qty = sum(detail.qty for detail in details)
        total_net_weight = sum(detail.net_weight for detail in details)
        purchase_data.append({
            'purchase': purchase,
            'total_qty': total_qty,
            'total_net_weight': total_net_weight,
        })

    context = {
        'purchases': purchase_data,
        'is_admin_like': is_admin_like,
    }
    return render(request, 'purchase_list.html', context)

@login_required(login_url='login')
def purchase_view(request, pk):
    is_admin_like = request.user.role in ['super_admin', 'admin']
    purchase = get_object_or_404(Purchase, pk=pk, delete_status=False)
    
    # Restrict non-admin users to their branch
    if not is_admin_like and purchase.branch != request.user.branch:
        messages.error(request, "You are not authorized to view this purchase.")
        return redirect('purchase_list')

    if request.method == "POST":
        if not is_admin_like:
            messages.error(request, "You are not authorized to update this purchase.")
            return redirect('purchase_list')
        
        form = PurchaseForm(request.POST, instance=purchase, user=request.user)
        formset = PurchaseDetailFormSet(request.POST, instance=purchase)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                # Update purchase
                purchase = form.save(commit=False)
                purchase.updated_by = request.user
                purchase.save()

                # Revert stock for deleted or updated items
                for detail in formset:
                    if detail.instance.pk and detail.cleaned_data.get('DELETE'):
                        item = detail.instance.item
                        if item.category.is_weight_based:
                            item.stock -= detail.instance.net_weight
                        else:
                            item.stock -= detail.instance.qty
                        item.save()
                    elif detail.cleaned_data and not detail.cleaned_data.get('DELETE'):
                        detail_instance = detail.save(commit=False)
                        detail_instance.purchase = purchase
                        # Revert old stock
                        if detail.instance.pk:
                            old_item = detail.instance.item
                            if old_item.category.is_weight_based:
                                old_item.stock -= detail.instance.net_weight
                            else:
                                old_item.stock -= detail.instance.qty
                            old_item.save()
                        # Update new stock
                        detail_instance.save()
                        item = detail.cleaned_data['item']
                        if item.category.is_weight_based:
                            item.stock += detail.cleaned_data['net_weight']
                        else:
                            item.stock += detail.cleaned_data['qty']
                        item.save()
                formset.save()
                messages.success(request, f"Purchase {purchase.invoice_number} updated successfully!")
                return redirect('purchase_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PurchaseForm(instance=purchase, user=request.user)
        formset = PurchaseDetailFormSet(instance=purchase)

    context = {
        'form': form,
        'formset': formset,
        'purchase': purchase,
        'is_admin_like': is_admin_like,
        'reset_form': False
    }
    return render(request, 'purchase_view.html', context)

@login_required(login_url='login')
def purchase_delete(request, pk):
    is_admin_like = request.user.role in ['super_admin', 'admin']
    if not is_admin_like:
        messages.error(request, "You are not authorized to delete this purchase.")
        return redirect('purchase_list')

    purchase = get_object_or_404(Purchase, pk=pk, delete_status=False)
    with transaction.atomic():
        # Revert stock
        for detail in purchase.details.all():
            item = detail.item
            if item.category.is_weight_based:
                item.stock -= detail.net_weight
            else:
                item.stock -= detail.qty
            item.save()
        # Update delete status and deleted_by
        purchase.delete_status = True
        purchase.deleted_by = request.user
        purchase.save()
        messages.success(request, f"Purchase {purchase.invoice_number} deleted successfully.")
    return redirect('purchase_list')

@login_required
def retail_sales_add(request):
    is_admin_like = request.user.role in ['super_admin', 'admin', 'manager']
    if request.method == "POST":
        form = RetailSalesForm(request.POST, user=request.user)
        formset = RetailSalesDetailFormSet(request.POST)
        customer_form = CustomerForm(request.POST)
        if form.is_valid() and formset.is_valid() and customer_form.is_valid():
            receipt_no = form.cleaned_data['receipt_no']
            if RetailSales.objects.filter(receipt_no=receipt_no).exists():
                messages.error(request, f"Receipt number {receipt_no} already exists!")
                return render(request, "retail_sales_add.html", {
                    'form': form,
                    'formset': formset,
                    'customer_form': customer_form,
                    'is_admin_like': is_admin_like
                })
            with transaction.atomic():
                sales = form.save(commit=False)
                sales.added_by = request.user
                if not is_admin_like:
                    sales.branch = request.user.branch
                customer_data = customer_form.cleaned_data
                customer_id = request.POST.get('customer_id')
                if customer_id:
                    sales.customer = Customer.objects.get(id=customer_id)
                elif customer_data['customer_name'] or customer_data['customer_phone']:
                    sales.customer = Customer.objects.create(
                        customer_name=customer_data['customer_name'] or '',
                        customer_phone=customer_data['customer_phone'] or '',
                        customer_address=customer_data['customer_address'] or '',
                        gstin=customer_data['gstin'] or ''
                    )
                sales.save()
                for detail in formset:
                    if detail.cleaned_data and not detail.cleaned_data.get('DELETE'):
                        detail_instance = detail.save(commit=False)
                        detail_instance.sales = sales
                        detail_instance.save()
                        item = detail.cleaned_data['item']
                        if item.category.is_weight_based:
                            item.stock -= detail.cleaned_data['net_weight']
                        else:
                            item.stock -= detail.cleaned_data['qty']
                        item.save()
                messages.success(request, f"Sales {receipt_no} saved successfully!")
                return redirect("dashboard")
        else:
            messages.error(request, "Please correct the errors below.")
            return render(request, "retail_sales_add.html", {
                'form': form,
                'formset': formset,
                'customer_form': customer_form,
                'is_admin_like': is_admin_like
            })
    else:
        initial = {
            'receipt_no': generate_next_receipt(),
            'sales_date': date.today(),
            'payment_mode': 'cash',
        }
        if not is_admin_like and request.user.branch:
            initial['branch'] = request.user.branch
        form = RetailSalesForm(initial=initial, user=request.user)
        customer_form = CustomerForm()
        if not is_admin_like:
            form.fields['sales_date'].widget.attrs['readonly'] = True
        formset = RetailSalesDetailFormSet(queryset=RetailSalesDetails.objects.none())
    return render(request, "retail_sales_add.html", {
        'form': form,
        'formset': formset,
        'customer_form': customer_form,
        'is_admin_like': is_admin_like
    })

@login_required
def wholesale_sales_add(request):
    is_admin_like = request.user.role in ['super_admin', 'admin', 'manager']
    if request.method == "POST":
        form = WholesaleSalesForm(request.POST, user=request.user)
        formset = WholesaleSalesDetailFormSet(request.POST)
        customer_form = CustomerForm(request.POST)
        if form.is_valid() and formset.is_valid() and customer_form.is_valid():
            receipt_no = form.cleaned_data['receipt_no']
            if WholesaleSales.objects.filter(receipt_no=receipt_no).exists():
                messages.error(request, f"Receipt number {receipt_no} already exists!")
                return render(request, "wholesale_sales_add.html", {
                    'form': form,
                    'formset': formset,
                    'customer_form': customer_form,
                    'is_admin_like': is_admin_like
                })
            with transaction.atomic():
                sales = form.save(commit=False)
                sales.added_by = request.user
                if not is_admin_like:
                    sales.branch = request.user.branch
                customer_data = customer_form.cleaned_data
                customer_id = request.POST.get('customer_id')
                if customer_id:
                    sales.customer = Customer.objects.get(id=customer_id)
                elif customer_data['customer_name'] or customer_data['customer_phone']:
                    sales.customer = Customer.objects.create(
                        customer_name=customer_data['customer_name'] or '',
                        customer_phone=customer_data['customer_phone'] or '',
                        customer_address=customer_data['customer_address'] or '',
                        gstin=customer_data['gstin'] or ''
                    )
                sales.save()
                for detail in formset:
                    if detail.cleaned_data and not detail.cleaned_data.get('DELETE'):
                        detail_instance = detail.save(commit=False)
                        detail_instance.sales = sales
                        detail_instance.save()
                        item = detail.cleaned_data['item']
                        if item.category.is_weight_based:
                            item.stock -= detail.cleaned_data['net_weight']
                        else:
                            item.stock -= detail.cleaned_data['qty']
                        item.save()
                messages.success(request, f"Wholesale Sales {receipt_no} saved successfully!")
                return redirect("dashboard")
        else:
            messages.error(request, "Please correct the errors below.")
            return render(request, "wholesale_sales_add.html", {
                'form': form,
                'formset': formset,
                'customer_form': customer_form,
                'is_admin_like': is_admin_like
            })
    else:
        initial = {
            'sales_date': date.today(),
            'payment_mode': 'pending',
            'paid_amount': 0,
        }
        if not is_admin_like and request.user.branch:
            initial['branch'] = request.user.branch
        form = WholesaleSalesForm(initial=initial, user=request.user)
        customer_form = CustomerForm()
        if not is_admin_like:
            form.fields['sales_date'].widget.attrs['readonly'] = True
        formset = WholesaleSalesDetailFormSet(queryset=WholesaleSalesDetails.objects.none())
    return render(request, "wholesale_sales_add.html", {
        'form': form,
        'formset': formset,
        'customer_form': customer_form,
        'is_admin_like': is_admin_like
    })

def generate_next_receipt():
    last = RetailSales.objects.order_by('-id').first()
    if last:
        try:
            prefix, num_str = last.receipt_no.rsplit('-', 1)
            if prefix == 'RS':
                num = int(num_str) + 1
                return f'RS-{num:04d}'
        except ValueError:
            pass
    return 'RS-0001'

@require_GET
def search_items(request):
    q = request.GET.get('q', '')
    items = Item.objects.filter(name__icontains=q)
    data = [
        {
            'id': item.id,
            'name': item.name,
            'code': item.code,
            'price': str(item.price_per_unit_retail),
            'is_weight_based': item.category.is_weight_based
        } for item in items
    ]
    return JsonResponse(data, safe=False)

@require_GET
def item_by_code(request):
    code = request.GET.get('code', '')
    try:
        item = Item.objects.get(code=code)
        data = {
            'id': item.id,
            'name': item.name,
            'price': str(item.price_per_unit_retail),
            'is_weight_based': item.category.is_weight_based
        }
        return JsonResponse(data)
    except Item.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)

@require_GET
def search_customers(request):
    q = request.GET.get('q', '')
    type_ = request.GET.get('type', 'name')
    if type_ == 'phone':
        customers = Customer.objects.filter(customer_phone__icontains=q)
    else:
        customers = Customer.objects.filter(customer_name__icontains=q)
    data = [
        {
            'id': c.id,
            'name': c.customer_name,
            'phone': c.customer_phone,
            'address': c.customer_address,
            'gstin': c.gstin
        } for c in customers
    ]
    return JsonResponse(data, safe=False)

@require_GET
def item_details(request, item_id):
    try:
        item = Item.objects.get(id=item_id)
        return JsonResponse({'is_weight_based': item.category.is_weight_based})
    except Item.DoesNotExist:
        return JsonResponse({'error': 'Item not found', 'is_weight_based': False}, status=404)