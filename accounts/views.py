from django.templatetags.static import static
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, F, Q
from django.contrib import messages
from django.conf import settings
import os
from django.forms import modelformset_factory
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from .forms import DailyStockUpdateForm,YieldPercentageForm,ExpenseCategoryForm,ExpenseForm,EmployeeLoginForm,PurchaseForm, PurchaseDetailFormSet, ItemCategoryForm, BranchForm, SupplierForm, ItemForm, RetailSalesForm, RetailSalesDetailFormSet, CustomerDataForm, WholesaleSalesForm, WholesaleSalesDetailFormSet,SupplierpayForm,EmployeForm,AttendanceInlineForm,CustomerForm,WholesalePaymentForm
from .models import DailystockUpdate,YieldPercentage,ExpenseCategory,Expense,Purchase, PurchaseDetail, Branch, Supplier, ItemCategory, Item, RetailSales, RetailSalesDetails, Customer, WholesaleSales, WholesaleSalesDetails,Supplierpay,Employe,Attendance,WholesalePayment
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.http import HttpRequest
from datetime import datetime, date,timedelta
from django.contrib.auth.hashers import make_password
from django.db import models
from decimal import Decimal,ROUND_HALF_UP
from django.utils import timezone
from django.db.models import IntegerField
from django.db.models.functions import Cast
from collections import OrderedDict
import base64
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from io import BytesIO
from django.utils.timezone import now

logger = logging.getLogger(__name__)

logo_path = os.path.join(
    settings.BASE_DIR,
    'static',
    'img',
    'jaan_logo.jpeg'
)

def render_to_pdf(template_src, context):
    html = render_to_string(template_src, context)
    result = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=result)

    if pisa_status.err:
        return None
    return result.getvalue()

@login_required
def wholesale_customer_balance(request):
    customer_id = request.GET.get('customer_id')

    if not customer_id:
        return JsonResponse({'balance': '0.00'})

    try:
        customer = Customer.objects.get(id = customer_id,delete_status=False)
    except Customer.DoesNotExist:
         return JsonResponse({'balance': '0.00'})

    total_sales = WholesaleSales.objects.filter(
            customer=customer,
            delete_status=False
        ).aggregate(total=Sum('grand_total'))['total'] or Decimal('0.00')

    total_paid = WholesalePayment.objects.filter(
        customer = customer,
        delete_status = False
    ).aggregate(paid=Sum('amount'))['paid'] or Decimal('0.00')

    opening_balance = customer.opening_balance or Decimal('0.00')

    balance = opening_balance + total_sales - total_paid

    return JsonResponse({'balance':str(balance)})


@login_required
def toggle_category_stock(request, pk):
    if request.user.role not in ['admin', 'super_admin']:
        messages.error(request, "Permission denied")
        return redirect('category_list')

    category = get_object_or_404(ItemCategory, pk=pk)
    category.include_in_stock_update = not category.include_in_stock_update
    category.save()

    messages.success(
        request,
        f"{category.category_name} updated for stock update"
    )
    return redirect('category_list')

@login_required
def daily_stock_report(request):

    from collections import OrderedDict
    from decimal import Decimal, ROUND_HALF_UP
    from django.shortcuts import get_object_or_404

    user = request.user
    role = user.role
    today = timezone.now().date()

    # ───────── DATE ─────────
    selected_date = request.GET.get('date', today)
    try:
        selected_date = datetime.strptime(str(selected_date), '%Y-%m-%d').date()
    except Exception:
        selected_date = today

    # ───────── BRANCH ─────────
    if role in ['admin', 'super_admin']:
        branch_id = request.GET.get('branch')
        branch = get_object_or_404(Branch, pk=branch_id) if branch_id else user.branch
    else:
        branch = user.branch

    # ───────── RECORDS ─────────
    records = (
        DailystockUpdate.objects
        .filter(date=selected_date, branch=branch)
        .select_related('item', 'item__category')
        .order_by('item__category__category_id', 'item__code')
    )

    category_items = OrderedDict()
    category_summary = {}

    for r in records:
        category_items.setdefault(r.item.category, []).append(r)

    # ───────── CALCULATIONS (MATCH JS EXACTLY) ─────────
    for category, rows in category_items.items():
        cid = category.pk

        summary = {
            'opening': Decimal('0'),
            'purchase': Decimal('0'),
            'total_stock': Decimal('0'),
            'sales': Decimal('0'),
            'live_used': Decimal('0'),
            'closing': Decimal('0'),
            'live_closing': Decimal('0'),       # totalLiveClosing
            'live_bird_closing': Decimal('0'),  # only live birds
            'total_live_available': Decimal('0'),
        }

        for r in rows:
            summary['opening'] += r.opening_stock
            summary['purchase'] += r.purchase_stock
            summary['total_stock'] += r.total_stock
            summary['sales'] += r.todays_sales
            summary['live_used'] += r.live_weight_derived
            summary['closing'] += r.closing_stock
            summary['live_closing'] += r.live_weight_closing

            if r.item.is_live:
                summary['total_live_available'] += r.total_stock
                summary['live_bird_closing'] += r.live_weight_closing

        # ─── FINAL VALUES (JS FORMULA) ───
        summary['expected'] = (
            summary['total_live_available'] - summary['live_used']
        ).quantize(Decimal('0.000'), rounding=ROUND_HALF_UP)

        summary['actual'] = (
            summary['live_bird_closing'] + summary['live_closing']
        ).quantize(Decimal('0.000'), rounding=ROUND_HALF_UP)

        summary['loss'] = (
            summary['expected'] - summary['actual']
        ).quantize(Decimal('0.000'), rounding=ROUND_HALF_UP)

        summary['loss_pct'] = (
            (summary['loss'] / summary['total_live_available']) * 100
            if summary['total_live_available'] > 0 else Decimal('0.00')
        )

        category_summary[cid] = summary
        category.summary = summary

    return render(request, 'daily_stock_report.html', {
        'category_items': category_items,
        'selected_date': selected_date,
        'branch': branch,
        'branches': Branch.objects.all(),
        'role': role,
    })




@login_required
def daily_stock_update(request):

    from collections import OrderedDict
    from decimal import Decimal, ROUND_HALF_UP
    from django.forms import modelformset_factory
    from django.db.models.functions import Cast
    from django.db.models import IntegerField
    from django.shortcuts import get_object_or_404

    user = request.user
    role = user.role
    today = timezone.now().date()

    # ───────── DATE ─────────
    if role == 'super_admin':
        selected_date = request.GET.get('date', today)
        try:
            selected_date = datetime.strptime(str(selected_date), '%Y-%m-%d').date()
        except Exception:
            selected_date = today
    else:
        selected_date = today

    # ───────── BRANCH ─────────
    if role in ['admin', 'super_admin']:
        branch_id = request.GET.get('branch')
        branch = get_object_or_404(Branch, pk=branch_id) if branch_id else user.branch
    else:
        branch = user.branch

    # ───────── ITEMS ─────────
    items_qs = (
        Item.objects
        .filter(category__include_in_stock_update=True)
        .annotate(code_int=Cast('code', IntegerField()))
        .select_related('category')
        .order_by('category__category_id', 'code_int')
    )

    # ───────── GROUP BY CATEGORY ─────────
    category_items = OrderedDict()
    for item in items_qs:
        category_items.setdefault(item.category, []).append(item)

    for cat, items in category_items.items():
        live_items = [i for i in items if i.is_live]
        non_live_items = sorted(
            [i for i in items if not i.is_live],
            key=lambda x: x.code_int or 0
        )
        category_items[cat] = live_items + non_live_items

    # ───────── EXISTING RECORDS ─────────
    existing = DailystockUpdate.objects.filter(
        date=selected_date,
        branch=branch
    ).select_related('item')

    existing_map = {e.item_id: e for e in existing}

    initial_data = []
    category_summary = {}

    # ───────── BUILD DATA ─────────
    for category, items in category_items.items():
        cid = category.pk

        category_summary[cid] = {
            'opening': Decimal('0'),
            'purchase': Decimal('0'),
            'sales': Decimal('0'),
            'closing_stock': Decimal('0'),
            'live_closing': Decimal('0'),
            'live_bird_closing': Decimal('0'),  # ✅ REQUIRED
            'total_live_available': Decimal('0'),
            'live_used': Decimal('0'),
        }

        for item in items:
            yp = item.yieldpercentage_set.first()
            multiplier = yp.multipler if yp else Decimal('1')

            opening = get_previous_closing_stock(item, selected_date, branch)
            purchase = get_purchase_stock(item, selected_date, branch)
            sales = get_todays_sales(item, selected_date, branch)
            total_stock = opening + purchase

            # Live used
            if item.is_live:
                category_summary[cid]['total_live_available'] += total_stock
                live_used = (sales * multiplier).quantize(
                    Decimal('0.000'), rounding=ROUND_HALF_UP
                )
            else:
                live_used = ((sales - purchase) * multiplier).quantize(
                    Decimal('0.000'), rounding=ROUND_HALF_UP
                )

            existing_row = existing_map.get(item.id)
            closing_stock = existing_row.closing_stock if existing_row else Decimal('0')

            # ✅ STEP 2 — MATCH JS EXACTLY
            live_closing = (closing_stock * multiplier).quantize(
                Decimal('0.000'), rounding=ROUND_HALF_UP
            )

            category_summary[cid]['opening'] += opening
            category_summary[cid]['purchase'] += purchase
            category_summary[cid]['sales'] += sales
            category_summary[cid]['closing_stock'] += closing_stock
            category_summary[cid]['live_closing'] += live_closing
            category_summary[cid]['live_used'] += live_used

            if item.is_live:
                category_summary[cid]['live_bird_closing'] += live_closing

            initial_data.append({
                'item': item.id,
                'item_obj': item,
                'multiplier': multiplier,
                'opening_stock': opening,
                'purchase_stock': purchase,
                'total_stock': total_stock,
                'todays_sales': sales,
                'closing_stock': closing_stock,
                'live_weight_derived': live_used,
                'live_weight_closing': live_closing,
            })

    # ───────── FINAL CALCULATIONS (MATCH JS) ─────────
    for s in category_summary.values():
        s['expected'] = (s['total_live_available'] - s['live_used']).quantize(
            Decimal('0.000'), rounding=ROUND_HALF_UP
        )

        s['actual'] = (
            s['live_bird_closing'] + s['live_closing']
        ).quantize(Decimal('0.000'), rounding=ROUND_HALF_UP)

        s['loss'] = (s['expected'] - s['actual']).quantize(
            Decimal('0.000'), rounding=ROUND_HALF_UP
        )

        s['loss_pct'] = (
            (s['loss'] / s['total_live_available']) * 100
            if s['total_live_available'] > 0 else Decimal('0.00')
        )

    for cat in category_items:
        cat.summary = category_summary[cat.pk]

    # ───────── FORMSET ─────────
    DailyStockFormSet = modelformset_factory(
        DailystockUpdate,
        form=DailyStockUpdateForm,
        extra=len(initial_data),
        can_delete=False
    )

    formset = DailyStockFormSet(
        request.POST or None,
        queryset=existing,
        initial=initial_data
    )

    # ───────── SAVE ─────────
    if request.method == 'POST' and formset.is_valid():

        for form, init in zip(formset.forms, initial_data):

            instance = form.save(commit=False)

            # ✅ FORCE item assignment (CRITICAL FIX)
            item = form.cleaned_data.get('item')
            if not item:
                item = Item.objects.get(pk=init['item'])

            instance.item = item
            instance.date = selected_date
            instance.branch = branch
            instance.updated_by = user

            # ✅ Live closing calculation (MATCH JS)
            yp = item.yieldpercentage_set.first()
            multiplier = yp.multipler if yp else Decimal('1')

            closing_stock = Decimal(str(instance.closing_stock))
            multiplier = Decimal(str(multiplier))

            instance.live_weight_closing = (
                closing_stock * multiplier
            ).quantize(Decimal('0.000'), rounding=ROUND_HALF_UP)
            instance.save()

        messages.success(request, "Daily stock updated successfully")
        return redirect('daily_stock_update')

    return render(request, 'daily_stock_update.html', {
        'formset': formset,
        'category_items': category_items,
        'selected_date': selected_date,
        'branch': branch,
        'branches': Branch.objects.all(),
        'role': role,
    })



# Helper functions remain the same
def get_previous_closing_stock(item, current_date, branch):
    prev = DailystockUpdate.objects.filter(
        item=item,
        branch=branch,
        date__lt=current_date
    ).order_by('-date').first()
    return prev.closing_stock if prev else Decimal('0.000')


def get_purchase_stock(item, date, branch):
    total = PurchaseDetail.objects.filter(
        item=item,
        purchase__purchase_date=date,
        purchase__branch=branch,
        purchase__delete_status=False
    ).aggregate(total=Sum('net_weight'))['total'] or Decimal('0.000')
    return total


def get_todays_sales(item, date, branch):
    retail = RetailSalesDetails.objects.filter(
        item=item,
        sales__sales_date=date,
        sales__branch=branch,
        sales__delete_status=False
    ).aggregate(total=Sum('net_weight'))['total'] or Decimal('0.000')

    wholesale = WholesaleSalesDetails.objects.filter(
        item=item,
        sales__sales_date=date,
        sales__branch=branch,
        sales__delete_status=False
    ).aggregate(total=Sum('net_weight'))['total'] or Decimal('0.000')

    return retail + wholesale

@login_required
def YieldPercentage_add(request):
    if request.method =="POST":
        form = YieldPercentageForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,"Values are added")
            return redirect('YieldPercentage_value_list')
    else:
        form = YieldPercentageForm()
    return render(request,'add_YieldPercentage_value.html',{'form': form})

@login_required    
def YieldPercentage_value_list(request):
    YieldPercentage_values = YieldPercentage.objects.filter()
    return render(request,'YieldPercentage_value_list.html',{'YieldPercentage_values':YieldPercentage_values})

@login_required
def YieldPercentage_update(request,pk):
    wastage_Values = get_object_or_404(YieldPercentage,pk=pk)
    if request.method =="POST":
        form = YieldPercentageForm(request.POST, instance = wastage_Values)
        if form.is_valid():
            form.save()
            messages.success(request,"Valued are Updated")
            return redirect('YieldPercentage_value_list')
    else:
        form = YieldPercentageForm(instance = wastage_Values)
    return render(request, 'add_YieldPercentage_value.html',{'form': form, 'wastage_Values':wastage_Values})


@login_required
def dashboard_view(request):
    user = request.user
    branch = user.branch if user.branch else None
    is_admin_like = user.role in ['super_admin', 'admin']

    # === FILTERS ===
    period = request.GET.get('period', 'month')
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    today = date.today()

    # Determine date range
    if period == 'week':
        from_date = today - timedelta(days=today.weekday())  # Monday
        to_date = from_date + timedelta(days=6)
    elif period == 'month':
        from_date = today.replace(day=1)
        to_date = today
    elif period == 'year':
        from_date = today.replace(month=1, day=1)
        to_date = today
    else:  # custom
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date() if from_date_str else today - timedelta(days=30)
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date() if to_date_str else today
        except:
            from_date = today - timedelta(days=30)
            to_date = today

    # Apply branch filter
    purchase_filter = Q(delete_status=False, purchase_date__range=[from_date, to_date])
    retail_filter = Q(delete_status=False, sales_date__range=[from_date, to_date])
    wholesale_filter = Q(delete_status=False, sales_date__range=[from_date, to_date])

    if not is_admin_like and branch:
        purchase_filter &= Q(branch=branch)
        retail_filter &= Q(branch=branch)
        wholesale_filter &= Q(branch=branch)

    # === TODAY'S SUMMARY ===
    today_purchase = Purchase.objects.filter(purchase_filter & Q(purchase_date=today)).aggregate(s=Sum('grand_total'))['s'] or 0
    today_retail = RetailSales.objects.filter(retail_filter & Q(sales_date=today)).aggregate(s=Sum('grand_total'))['s'] or 0
    today_wholesale = WholesaleSales.objects.filter(wholesale_filter & Q(sales_date=today)).aggregate(s=Sum('grand_total'))['s'] or 0
    today_sales = today_retail + today_wholesale
    today_profit = today_sales - today_purchase
    pending_credit = RetailSales.objects.filter(payment_mode='pending', delete_status=False).aggregate(s=Sum('grand_total'))['s'] or 0

    # === CHART DATA ===
    # Generate all dates in range
    delta = to_date - from_date
    date_range = [from_date + timedelta(days=i) for i in range(delta.days + 1)]

    # Labels (format based on period)
    if period == 'week':
        labels = [d.strftime('%a %d') for d in date_range]  # Mon 02, Tue 03...
    elif delta.days <= 40:
        labels = [d.strftime('%b %d') for d in date_range]  # Jan 02
    else:
        labels = [d.strftime('%b %Y') for d in date_range]  # Jan 2026

    # Aggregate purchases
    purchases = Purchase.objects.filter(purchase_filter).values('purchase_date').annotate(total=Sum('grand_total')).order_by('purchase_date')
    purchase_map = {p['purchase_date']: float(p['total'] or 0) for p in purchases}
    purchase_data = [purchase_map.get(d, 0) for d in date_range]

    # Aggregate retail sales
    retail = RetailSales.objects.filter(retail_filter).values('sales_date').annotate(total=Sum('grand_total')).order_by('sales_date')
    retail_map = {r['sales_date']: float(r['total'] or 0) for r in retail}
    retail_data = [retail_map.get(d, 0) for d in date_range]

    # Aggregate wholesale sales
    wholesale = WholesaleSales.objects.filter(wholesale_filter).values('sales_date').annotate(total=Sum('grand_total')).order_by('sales_date')
    wholesale_map = {w['sales_date']: float(w['total'] or 0) for w in wholesale}
    wholesale_data = [wholesale_map.get(d, 0) for d in date_range]

    context = {
        'user': user,
        'branch_name': branch.branch_name if branch else 'All Branches',

        # Today's cards
        'today_sales': today_sales,
        'today_purchase': today_purchase,
        'today_profit': today_profit,
        'pending_credit': pending_credit,

        # Chart data
        'labels': labels,
        'purchase_data': purchase_data,
        'retail_sales_data': retail_data,
        'wholesale_sales_data': wholesale_data,

        # Filters (for form)
        'period': period,
        'from_date': from_date_str or from_date.strftime('%Y-%m-%d'),
        'to_date': to_date_str or to_date.strftime('%Y-%m-%d'),
    }

    return render(request, 'dashboard.html', context)

@login_required
def expense_category_list(request):
    categories = ExpenseCategory.objects.filter(delete_status=False).order_by('expense_name')
    return render(request, 'expense_category_list.html', {'categories': categories})

@login_required
def expense_category_add(request):
    if request.method == "POST":
        form = ExpenseCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense category added successfully!")
            return redirect('expense_category_list')
    else:
        form = ExpenseCategoryForm()
    return render(request, 'expense_category_add.html', {'form': form})

@login_required
def expense_category_update(request, pk):
    category = get_object_or_404(ExpenseCategory, pk=pk, delete_status=False)
    if request.method == "POST":
        form = ExpenseCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense category updated successfully!")
            return redirect('expense_category_list')
    else:
        form = ExpenseCategoryForm(instance=category)
    return render(request, 'expense_category_add.html', {'form': form, 'category': category})

@login_required
def expense_category_delete(request, pk):
    category = get_object_or_404(ExpenseCategory, pk=pk, delete_status=False)
    if request.method == "POST":
        category.delete_status = True
        category.save()
        messages.success(request, "Expense category deleted successfully.")
        return redirect('expense_category_list')
    return render(request, 'expense_category_delete.html', {'category': category})

@login_required
def expense_add(request):
    if request.method == "POST":
        form = ExpenseForm(request.POST, user=request.user)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.save()
            messages.success(request, f"Expense ₹{expense.amount} recorded!")
            return redirect('expense_list')
    else:
        form = ExpenseForm(user=request.user)
    return render(request, 'expense_add.html', {'form': form})

@login_required
def expense_list(request):
    user = request.user
    is_admin_like = user.role in ['admin', 'super_admin']

    # Filters
    branch_id = request.GET.get('branch')
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')

    expenses = Expense.objects.filter(delete_status=False).select_related('expense', 'staff', 'branch')

    if from_date_str:
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            expenses = expenses.filter(payment_date__gte=from_date)
        except:
            pass
    if to_date_str:
        try:
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
            expenses = expenses.filter(payment_date__lte=to_date)
        except:
            pass

    selected_branch = None
    if is_admin_like:
        if branch_id and branch_id.isdigit():
            expenses = expenses.filter(branch_id=branch_id)
            selected_branch = Branch.objects.filter(branch_id=branch_id).first()
    else:
        if user.branch:
            expenses = expenses.filter(branch=user.branch)
            selected_branch = user.branch
        else:
            expenses = expenses.none()

    expenses = expenses.order_by('-payment_date')

    context = {
        'expenses': expenses,
        'branches': Branch.objects.all() if is_admin_like else [],
        'is_admin_like': is_admin_like,
        'selected_branch': selected_branch,
        'from_date': from_date_str,
        'to_date': to_date_str,
        'today': date.today().strftime('%Y-%m-%d'),
    }
    return render(request, 'expense_list.html', context)

@login_required
def wholesale_payment_add(request):
    if request.method == "POST":
        form = WholesalePaymentForm(request.POST, user=request.user)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.added_by = request.user
            if not payment.branch and request.user.branch:
                payment.branch = request.user.branch
            payment.save()
            messages.success(request, f"Payment of ₹{payment.amount} recorded for {payment.customer}!")
            return redirect('wholesale_payment_list')
    else:
        form = WholesalePaymentForm(user=request.user)

    return render(request, "wholesale_payment_add.html", {"form": form})

@login_required
def wholesale_payment_list(request):
    user = request.user
    is_admin_like = user.role in ['admin', 'super_admin']

    customer_id = request.GET.get('customer')
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')

    payments = WholesalePayment.objects.filter(delete_status=False).select_related('customer', 'branch', 'added_by')

    if from_date_str:
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            payments = payments.filter(payment_date__gte=from_date)
        except:
            pass
    if to_date_str:
        try:
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
            payments = payments.filter(payment_date__lte=to_date)
        except:
            pass
    if customer_id:
        payments = payments.filter(customer_id=customer_id)

    if not is_admin_like and user.branch:
        payments = payments.filter(branch=user.branch)

    payments = payments.order_by('-payment_date')

    

    # Customer balance calculation
    customers = Customer.objects.filter(whole_sale=True, delete_status=False)
    if not is_admin_like and user.branch:
        customers = customers.filter(wholesalesales__branch=user.branch).distinct()

    customer_stats = []
    for cust in customers:
        total_sales = WholesaleSales.objects.filter(
            customer=cust,
            delete_status=False
        ).aggregate(total=Sum('grand_total'))['total'] or Decimal('0.00')

        total_paid = WholesalePayment.objects.filter(
            customer=cust,
            delete_status=False
        ).aggregate(paid=Sum('amount'))['paid'] or Decimal('0.00')

        opening_balance = cust.opening_balance or Decimal('0.00')

        balance = opening_balance + total_sales - total_paid

        if balance > 0:  # Only show if pending
            customer_stats.append({
                'customer': cust,
                'total_sales': total_sales,
                'total_paid': total_paid,
                'balance': balance,
                'opening_balance': opening_balance
            })

    context = {
        'payments': payments,
        'customers': Customer.objects.filter(whole_sale=True, delete_status=False),
        'customer_stats': customer_stats,
        'selected_customer': customer_id,
        'is_admin_like': is_admin_like,
    }
    return render(request, 'wholesale_payment_list.html', context)

@login_required(login_url='login')
def wholesale_item_report(request):
    is_admin_like = request.user.role in ['super_admin', 'admin']
    
    # Get filter parameters
    branch_id = request.GET.get('branch')
    customer_id = request.GET.get('customer')
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    export_type = request.GET.get('export')

    today = date.today()
    from_date = from_date_str or today.strftime('%Y-%m-%d')
    to_date = to_date_str or today.strftime('%Y-%m-%d')

    # Parse dates safely
    try:
        from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
    except ValueError:
        from_date_obj = today
        from_date = today.strftime('%Y-%m-%d')

    try:
        to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
    except ValueError:
        to_date_obj = today
        to_date = today.strftime('%Y-%m-%d')

    # Base queryset - only wholesale sales (not retail)
    details_qs = WholesaleSalesDetails.objects.filter(
        sales__delete_status=False,
        sales__sales_date__gte=from_date_obj,
        sales__sales_date__lte=to_date_obj
    ).select_related(
        'sales__customer', 'sales__branch', 'item'
    )

    # Apply branch filter
    selected_branch = None
    selected_customer = None

    if is_admin_like:
        if branch_id and branch_id.isdigit():
            details_qs = details_qs.filter(sales__branch_id=branch_id)
            selected_branch = Branch.objects.filter(branch_id=branch_id).first()
    else:
        # Non-admin: only their branch
        if request.user.branch:
            details_qs = details_qs.filter(sales__branch=request.user.branch)
            selected_branch = request.user.branch
        else:
            details_qs = details_qs.none()

    #apply customer filter
    if customer_id:
        details_qs = details_qs.filter(sales__customer_id=customer_id)
        selected_customer = Customer.objects.filter(id=customer_id).first()

    # Group by Customer → Item
    report_data = {}
    for detail in details_qs:
        customer = detail.sales.customer
        customer_name = customer.customer_name or "Unknown Customer"
        item = detail.item

        if customer_name not in report_data:
            report_data[customer_name] = {
                'customer': customer,
                'items': {}
            }

        item_key = item.code
        if item_key not in report_data[customer_name]['items']:
            report_data[customer_name]['items'][item_key] = {
                'code': item.code,
                'name': item.name,
                'total_qty': 0,
                'total_net_weight': Decimal('0.00'),
                'total_amount': Decimal('0.00')
            }

        item_data = report_data[customer_name]['items'][item_key]
        item_data['total_qty'] += detail.qty
        item_data['total_net_weight'] += detail.net_weight or Decimal('0.00')
        item_data['total_amount'] += detail.total_amount or Decimal('0.00')


    # Sort customers alphabetically
    sorted_report = dict(sorted(report_data.items()))

    context = {
        'report_data': sorted_report,
        'is_admin_like': is_admin_like,
        'branches': Branch.objects.all() if is_admin_like else [],
        'selected_branch': selected_branch,
        'customers': Customer.objects.filter(whole_sale=True, delete_status=False),
        'selected_customer': selected_customer,
        'from_date': from_date,
        'to_date': to_date,
        'today': today.strftime('%Y-%m-%d'),
        'logo_path': logo_path,
    }

    # ================= PDF EXPORT ⭐ NEW =================
    if export_type == 'pdf':
        today_str = now().strftime('%Y-%m-%d')

        if selected_customer:
            cust_name = selected_customer.customer_name.replace(' ', '_')
        else:
            cust_name = 'All_Customers'

        filename = f"{today_str}-{cust_name}.pdf"

        pdf = render_to_pdf('wholesale_item_report_pdf.html', context)

        if not pdf:
            return HttpResponse("PDF generation error", status=500)

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    return render(request, 'wholesale_item_report.html', context)

@login_required(login_url='login')
def retail_pay_credit(request, pk):
    sale = get_object_or_404(RetailSales, pk=pk, delete_status=False)

    if request.method == "POST":

        payment_mode = request.POST.get('payment_mode')
        cash = request.POST.get('cash')
        upi = request.POST.get('upi')
        card = request.POST.get('card')
        pending = request.POST.get('pending')

        try:
            cash = Decimal(request.POST.get('cash') or 0)
            upi = Decimal(request.POST.get('upi') or 0)
            card = Decimal(request.POST.get('card') or 0)
            pending = Decimal(request.POST.get('pending') or 0)
        except ValueError:
            messages.error(request, "Invalid payment values.")
            return redirect('retail_sales_list')

        paid_total = cash + upi + card

        # 🔥 Important validation
        if paid_total <= 0:
            messages.error(request, "Payment amount must be greater than zero.")
            return redirect('retail_sales_list')

        # Calculate new pending
        remaining = sale.grand_total - (
            sale.total_cash + sale.total_upi + sale.total_card
        )

        # Update sale
        sale.payment_mode = payment_mode
        sale.total_cash += cash
        sale.total_upi += upi
        sale.total_card += card
        sale.pending_amount = pending

        sale.save()

        messages.success(
            request,
            f"Payment recorded for bill {sale.receipt_no}."
        )

        return redirect('retail_sales_list')

    return redirect('retail_sales_list')


@login_required(login_url='login')
def customer_list(request):
    customers = Customer.objects.filter(delete_status=False).order_by('customer_name', 'customer_phone')
    return render(request, 'customer_list.html', {'customers': customers})

@login_required(login_url='login')
def customer_add(request):
    if request.method == "POST":
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer added successfully!")
            return redirect('customer_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomerForm()
    return render(request, 'customer_add.html', {'form': form})

@login_required(login_url='login')
def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk, delete_status=False)
    if request.method == "POST":
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer updated successfully!")
            return redirect('customer_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'customer_add.html', {'form': form, 'customer': customer})

@login_required(login_url='login')
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk, delete_status=False)
    if request.method == "POST":
        customer.delete_status = True
        customer.save()
        messages.success(request, "Customer deleted successfully.")
        return redirect('customer_list')
    return render(request, 'customer_delete.html', {'customer': customer})

@login_required(login_url='login')
def retail_item_report(request):
    is_admin_like = request.user.role in ['super_admin', 'admin']
    
    # Get filter parameters
    branch_id = request.GET.get('branch')
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    export_type = request.GET.get('export')

    # Default: today
    today = date.today()
    from_date = from_date_str or today.strftime('%Y-%m-%d')
    to_date = to_date_str or today.strftime('%Y-%m-%d')

    # Parse dates safely
    try:
        from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
    except ValueError:
        from_date_obj = today
        from_date = today.strftime('%Y-%m-%d')

    try:
        to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
    except ValueError:
        to_date_obj = today
        to_date = today.strftime('%Y-%m-%d')

    # Base queryset for aggregation
    items_qs = RetailSalesDetails.objects.filter(
        sales__delete_status=False,
        sales__sales_date__gte=from_date_obj,
        sales__sales_date__lte=to_date_obj
    )

    # Apply branch filter
    selected_branch = None
    if is_admin_like:
        if branch_id and branch_id.isdigit():
            items_qs = items_qs.filter(sales__branch_id=branch_id)
            selected_branch = Branch.objects.filter(branch_id=branch_id).first()
    else:
        # Non-admin: only their branch
        if request.user.branch:
            items_qs = items_qs.filter(sales__branch=request.user.branch)
            selected_branch = request.user.branch
        else:
            items_qs = items_qs.none()

    # Aggregate per item
    item_data = items_qs.values(
        'item__code', 'item__name'
    ).annotate(
        total_qty=Sum('qty'),
        total_net_weight=Sum('net_weight'),
        total_amount=Sum('total_amount')
    ).order_by('item__name')

    # Convert to list (if needed for template)
    item_data = list(item_data)

    context = {
        'item_data': item_data,
        'is_admin_like': is_admin_like,
        'branches': Branch.objects.all() if is_admin_like else [],
        'selected_branch': selected_branch,
        'from_date': from_date,
        'to_date': to_date,
        'today': today.strftime('%Y-%m-%d'),
        'logo_path': logo_path,
    }

    if export_type == 'pdf':
        today_str = now().strftime('%Y-%m-%d')

        filename = f"{today_str}-retail-item-report.pdf"

        pdf = render_to_pdf('retail_item_report_pdf.html', context)

        if not pdf:
            return HttpResponse("PDF generation error", status=500)

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    
    return render(request, 'retail_item_report.html', context)

@login_required
def employee_login_create(request):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, "You are not authorized.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = EmployeeLoginForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Login created for {user.get_full_name() or user.username}")
            return redirect('employee_login_create')
    else:
        form = EmployeeLoginForm()

    return render(request, 'employee_login_create.html', {'form': form})

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
        form = SupplierpayForm(request.POST, user=request.user)
        if form.is_valid():
            payment = form.save(commit=False)
            # Ensure branch is always saved
            if not payment.branch and request.user.branch:
                payment.branch = request.user.branch
            payment.save()
            messages.success(request, f"Payment of ₹{payment.amount} to {payment.supplier} recorded!")
            return redirect('supplier_payment_list')
    else:
        form = SupplierpayForm(user=request.user)

    return render(request, "supplier_pay.html", {"form": form})

@login_required
def supplier_payment_list(request):
    user = request.user
    is_manager = user.role == 'manager'
    is_staff = user.role == 'staff'
    is_admin_like = user.role in ['admin', 'super_admin']

    supplier_id = request.GET.get('supplier')
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')

    # === PAYMENTS LIST ===
    payments = Supplierpay.objects.filter(delete_status=False).select_related('supplier', 'branch')

    if from_date_str:
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            payments = payments.filter(payment_date__gte=from_date)
        except ValueError:
            pass
    if to_date_str:
        try:
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
            payments = payments.filter(payment_date__lte=to_date)
        except ValueError:
            pass
    if supplier_id:
        payments = payments.filter(supplier_id=supplier_id)

    # Branch restriction for manager/staff
    if is_manager or is_staff:
        if not user.branch:
            messages.error(request, "You are not assigned to any branch.")
            payments = payments.none()
        else:
            payments = payments.filter(branch=user.branch)

    payments = payments.order_by('-payment_date')

    # === SUPPLIER BALANCE CALCULATION ===
    stats = Supplier.objects.all()

    # Base filters
    purchase_q = Q(purchase__delete_status=False)
    payment_q = Q(supplierpay__delete_status=False)

    # Apply branch filter if needed
    if is_manager or is_staff and user.branch:
        purchase_q &= Q(purchase__branch=user.branch)
        payment_q &= Q(supplierpay__branch=user.branch)

    # Apply supplier filter BEFORE annotate (safe)
    if supplier_id:
        stats = stats.filter(supplier_id=supplier_id)  # Use supplier_id, not id!

    supplier_stats = stats.annotate(
        total_purchase=Sum(
            'purchase__details__total_amount',
            filter=purchase_q,
            output_field=models.DecimalField(max_digits=12, decimal_places=2)
        ),
        total_paid=Sum(
            'supplierpay__amount',
            filter=payment_q,
            output_field=models.DecimalField(max_digits=12, decimal_places=2)
        )
    ).annotate(
        balance=F('total_purchase') - F('total_paid')
    ).values(
        'supplier_id', 'supplier_name', 'total_purchase', 'total_paid', 'balance'
    )

    # Clean None → 0.00
    supplier_stats = [
        {
            'supplier_id': s['supplier_id'],
            'supplier_name': s['supplier_name'],
            'total_purchase': s['total_purchase'] or Decimal('0.00'),
            'total_paid': s['total_paid'] or Decimal('0.00'),
            'balance': (s['total_purchase'] or Decimal('0.00')) - (s['total_paid'] or Decimal('0.00'))
        }
        for s in supplier_stats
    ]

    # Suppliers for dropdown
    if is_manager_or_staff := (is_manager or is_staff):
        suppliers = Supplier.objects.filter(
            purchase__branch=user.branch,
            purchase__delete_status=False
        ).distinct()
    else:
        suppliers = Supplier.objects.all()

    context = {
        'payments': payments,
        'suppliers': suppliers,
        'selected_supplier': supplier_id,
        'from_date': from_date_str,
        'to_date': to_date_str,
        'supplier_stats': supplier_stats,
        'is_manager': is_manager_or_staff,
        'is_admin_like': is_admin_like,
    }
    return render(request, 'supplier_payment_list.html', context)


@login_required
def supplier_payment_update(request, pk):
    if request.user.role not in ['admin', 'super_admin']:
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
    if request.user.role not in ['admin', 'super_admin']:
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
    items = Item.objects.all().order_by("code")
    return render(request, "item_list.html", {"items": items})


@login_required
def item_update(request, pk):
    item = get_object_or_404(Item, pk=pk)
    
    if request.method == "POST":
        form = ItemForm(request.POST, instance=item, user=request.user)  # ← PASS USER
        if form.is_valid():
            form.save()
            messages.success(request, "Item prices updated successfully!")
            return redirect('item_list')
    else:
        form = ItemForm(instance=item, user=request.user)  # ← PASS USER HERE TOO

    context = {
        'form': form,
        'item': item
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
    is_admin_like = request.user.role in ['super_admin', 'admin']
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
    
    # Get filter parameters
    branch_id = request.GET.get('branch')
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')

    # Default: today
    today = date.today()
    from_date = from_date_str
    to_date = to_date_str

    # Parse dates safely
    try:
        if from_date_str:
            from_date_obj = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        else:
            from_date_obj = today
    except ValueError:
        from_date_obj = today
        from_date = today.strftime('%Y-%m-%d')

    try:
        if to_date_str:
            to_date_obj = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        else:
            to_date_obj = today
    except ValueError:
        to_date_obj = today
        to_date = today.strftime('%Y-%m-%d')

    # Base queryset
    purchases = Purchase.objects.filter(
        delete_status=False,
        purchase_date__gte=from_date_obj,
        purchase_date__lte=to_date_obj
    ).select_related('supplier', 'branch', 'added_by')

    # Apply branch filter
    selected_branch = None
    if is_admin_like:
        if branch_id and branch_id.isdigit():
            purchases = purchases.filter(branch_id=branch_id)
            selected_branch = Branch.objects.filter(branch_id=branch_id).first()
    else:
        # Non-admin: only their branch
        if request.user.branch:
            purchases = purchases.filter(branch=request.user.branch)
            selected_branch = request.user.branch
        else:
            purchases = purchases.none()

    # Order by latest first
    purchases = purchases.order_by('-purchase_date', '-created_date')

    # Calculate totals for display
    purchase_data = []
    for purchase in purchases:
        details = purchase.details.all()
        total_qty = sum(d.qty for d in details)
        total_net_weight = sum(d.net_weight for d in details)
        purchase_data.append({
            'purchase': purchase,
            'total_qty': total_qty,
            'total_net_weight': total_net_weight,
        })

    context = {
        'purchases': purchase_data,
        'is_admin_like': is_admin_like,
        'branches': Branch.objects.all() if is_admin_like else [],
        'selected_branch': selected_branch,
        'from_date': from_date or today.strftime('%Y-%m-%d'),
        'to_date': to_date or today.strftime('%Y-%m-%d'),
        'today': today.strftime('%Y-%m-%d'),
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
        'purchase': purchase,
        'is_admin_like': is_admin_like,
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

def get_or_create_customer(data, customer_id=None):
    phone = data.get('customer_phone', '').strip()
    gstin = data.get('gstin', '').strip()

    # 1. If we have customer_id → reuse it directly
    if customer_id:
        try:
            return Customer.objects.get(id=customer_id), False
        except Customer.DoesNotExist:
            pass

    # 2. Try to find by phone (priority)
    if phone:
        try:
            customer = Customer.objects.get(customer_phone=phone)
            return customer, False  # REUSE!
        except Customer.DoesNotExist:
            pass

    # 3. Try by GSTIN
    if gstin:
        try:
            customer = Customer.objects.get(gstin=gstin)
            return customer, False
        except Customer.DoesNotExist:
            pass

    # 4. Only NOW create new (safe — no conflict)
    if data.get('customer_name') or phone or gstin:
        return Customer.objects.create(
            customer_name=data.get('customer_name', 'Customer') or 'Customer',
            customer_phone=phone or None,
            customer_address=data.get('customer_address', '') or '',
            gstin=gstin or None
        ), True

    # Fallback
    return Customer.objects.get_or_create(
        customer_name="Store Customer",
        defaults={'customer_phone': None, 'customer_address': '', 'gstin': None}
    )[0], False

def generate_next_receipt(branch_alias):

    if not branch_alias:
        branch_alias = "XX"  # fallback

    prefix = branch_alias.upper()

    # Find the last retail sale for this branch prefix
    last_sale = RetailSales.objects.filter(
        receipt_no__istartswith=prefix + '-',
        delete_status=False
    ).order_by('-id').first()

    if last_sale and '-' in last_sale.receipt_no:
        try:
            num_part = last_sale.receipt_no.split('-', 1)[1]
            num = int(''.join(filter(str.isdigit, num_part)))
            next_num = num + 1
            return f"{prefix}-{next_num:04d}"
        except (ValueError, IndexError):
            pass

    # If no valid last receipt or parsing failed
    return f"{prefix}-0001"

@login_required
def retail_receipt(request, pk):
    sale = get_object_or_404(RetailSales, pk=pk, delete_status=False)
    return render(request, 'retail_receipt.html', {'sale': sale})

from django.db.models import Max

def generate_next_receipt(branch_alias):
    """Generate next receipt like AK-0001, BK-0005"""
    if not branch_alias:
        branch_alias = "XX"
    prefix = branch_alias.upper().strip()

    # Get the highest number used with this prefix
    last = RetailSales.objects.filter(
        receipt_no__istartswith=prefix + '-',
        delete_status=False
    ).aggregate(max_id=Max('id'))

    if last['max_id']:
        # Try to extract number from existing receipts
        similar = RetailSales.objects.filter(
            receipt_no__istartswith=prefix + '-',
            delete_status=False
        ).order_by('-receipt_no').first()

        if similar and similar.receipt_no:
            try:
                num_part = similar.receipt_no.split('-')[1]
                num = int(''.join(filter(str.isdigit, num_part)))
                return f"{prefix}-{num + 1:04d}"
            except:
                pass

    return f"{prefix}-0001"


@login_required
def retail_sales_add(request):
    is_admin_like = request.user.role in ['super_admin', 'admin']

    if request.method == "POST":
        customer_id = request.POST.get('customer_id')
        take_away_emp_id = request.POST.get('take_amay_employee')
        require_customer = bool(take_away_emp_id and take_away_emp_id != '')

        form = RetailSalesForm(request.POST, user=request.user)
        formset = RetailSalesDetailFormSet(request.POST)
        customer_form = CustomerDataForm(request.POST, require_customer=require_customer)

        if form.is_valid() and formset.is_valid() and customer_form.is_valid():
            receipt_no = form.cleaned_data['receipt_no'].strip()

            # ONLY BLOCK IF AN ACTIVE (not deleted) RECEIPT EXISTS
            if RetailSales.objects.filter(
                receipt_no__iexact=receipt_no,
                delete_status=False
            ).exists():
                messages.error(request, f"Receipt number '{receipt_no}' is already in use (active sale exists)!")
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

                # === SAFE CUSTOMER HANDLING ===
                customer_data = customer_form.cleaned_data
                customer, created = get_or_create_customer(customer_data, customer_id)

                # Optional: Update existing customer if fields changed (safe)
                if not created and any(customer_data.values()):
                    for field, value in customer_data.items():
                        if value:
                            setattr(customer, field, value)
                    customer.save()

                sales.customer = customer
                sales.save()

                # Save items & deduct stock
                for detail in formset:
                    if detail.cleaned_data and not detail.cleaned_data.get('DELETE'):
                        detail_instance = detail.save(commit=False)
                        detail_instance.sales = sales
                        detail_instance.save()

                        item = detail.cleaned_data['item']
                        qty = detail.cleaned_data['qty'] or 0
                        net_weight = detail.cleaned_data['net_weight'] or 0

                        if item.category.is_weight_based:
                            if item.stock < net_weight:
                                messages.error(request, f"Low stock: {item.name}")
                                #raise transaction.TransactionManagementError()
                            item.stock -= net_weight
                        else:
                            if item.stock < qty:
                                messages.error(request, f"Low stock: {item.name}")
                                #raise transaction.TransactionManagementError()
                            item.stock -= qty
                        item.save()

                messages.success(request, f"Retail sale {receipt_no} saved successfully!")
                return redirect('retail_receipt', pk=sales.pk)

        else:
            messages.error(request, "Please correct the errors below.")

    else:
        # GET Request
        selected_branch = None
        if is_admin_like:
            branch_id = request.GET.get('branch')
            if branch_id:
                selected_branch = get_object_or_404(Branch, branch_id=branch_id)
            else:
                selected_branch = Branch.objects.first()
        else:
            selected_branch = request.user.branch

        receipt_no = generate_next_receipt(selected_branch.alias if selected_branch else "XX")

        initial = {
            'receipt_no': receipt_no,
            'sales_date': date.today(),
            'payment_mode': 'cash',
        }
        if selected_branch:
            initial['branch'] = selected_branch

        form = RetailSalesForm(initial=initial, user=request.user)
        form.fields['receipt_no'].widget.attrs['readonly'] = True

        customer_form = CustomerDataForm(require_customer=False)
        formset = RetailSalesDetailFormSet(queryset=RetailSalesDetails.objects.none())

    context = {
        'form': form,
        'formset': formset,
        'customer_form': customer_form,
        'is_admin_like': is_admin_like,
    }
    return render(request, "retail_sales_add.html", context)

from django.db.models import Q
from datetime import date

@login_required(login_url='login')
def retail_sales_list(request):
    is_admin_like = request.user.role in ['super_admin', 'admin']
    
    # === FILTER PARAMETERS ===
    branch_id = request.GET.get('branch')
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')

    today = date.today()

    # Default to today if no date provided
    from_date_str = from_date_str or today.strftime('%Y-%m-%d')
    to_date_str = to_date_str or today.strftime('%Y-%m-%d')

    # Parse dates safely
    try:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
    except ValueError:
        from_date = today

    try:
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
    except ValueError:
        to_date = today

    selected_branch = None
    if branch_id and branch_id.isdigit():
        selected_branch = int(branch_id)

    # === 1. PENDING CREDIT BILLS (Always show, no date filter) ===
    credit_sales = RetailSales.objects.filter(
        payment_mode='pending',
        delete_status=False
    ).select_related('branch', 'customer', 'added_by')



    if not is_admin_like:
        credit_sales = credit_sales.filter(branch=request.user.branch)
    else:
        if selected_branch is not None:
            credit_sales = credit_sales.filter(branch_id=selected_branch)

    credit_sales = credit_sales.order_by('-sales_date')

    # === 2. REGULAR FILTERED SALES (With date & branch filter) ===
    sales = RetailSales.objects.filter(
        delete_status=False,
        sales_date__gte=from_date,
        sales_date__lte=to_date
    ).select_related('branch', 'customer', 'added_by')

    # Apply branch filter
    if not is_admin_like:
        if request.user.branch:
            sales = sales.filter(branch=request.user.branch)
            selected_branch_name = request.user.branch.branch_name
        else:
            sales = sales.none()
            selected_branch_name = "No Branch Assigned"
    else:
        if selected_branch is not None:
            sales = sales.filter(branch_id=selected_branch)
        selected_branch_name = "All Branches"
        if selected_branch is not None:
            try:
                selected_branch_name = Branch.objects.get(branch_id=selected_branch).branch_name
            except Branch.DoesNotExist:
                selected_branch_name = "Unknown Branch"

    sales = sales.order_by('-sales_date')

    totals = sales.aggregate(
    total_subtotal = Sum('total'),
    total_discount = Sum('discount'),
    total_grand    = Sum('grand_total'),
    total_cash     = Sum('total_cash'),
    total_upi      = Sum('total_upi'),
    total_card     = Sum('total_card'),
    total_pending     = Sum('pending_amount'),
   )

    total_credits = credit_sales.aggregate(
        credit_total_grand    = Sum('grand_total'),
    )

    # === 3. GRAND TOTAL & PAYMENT MODE BREAKDOWN (Only for filtered sales) ===
    total_grand = sales.aggregate(total=Sum('grand_total'))['total'] or Decimal('0.00')

    payment_mode_totals = sales.values('payment_mode').annotate(
        total=Sum('grand_total')
    ).order_by('payment_mode')

    # Convert to display-friendly dict
    mode_display = {
        'cash': 'Cash',
        'upi': 'UPI',
        'online': 'Online',
        'cheque': 'Cheque',
        'pending': 'Pending',
    }
    payment_mode_totals_dict = {}
    for item in payment_mode_totals:
        mode = item['payment_mode']
        display_name = mode_display.get(mode, mode.title())
        payment_mode_totals_dict[display_name] = item['total'] or Decimal('0.00')

    
    # === CONTEXT ===
    context = {
        'sales': sales,
        'credit_sales': credit_sales,  # Pending credit bills
        'total_grand': total_grand,
        'payment_mode_totals': payment_mode_totals_dict,

        'branches': Branch.objects.all() if is_admin_like else [],
        'is_admin_like': is_admin_like,
        'selected_branch': selected_branch,
        'selected_branch_name': selected_branch_name,

        # For date inputs
        'from_date_str': from_date_str,
        'to_date_str': to_date_str,

        # For display
        'from_date': from_date,
        'to_date': to_date,
        'today': today.strftime('%Y-%m-%d'),

        'total_subtotal': totals['total_subtotal'] or Decimal('0.00'),
        'total_discount': totals['total_discount'] or Decimal('0.00'),
        'total_grand': totals['total_grand'] or Decimal('0.00'),

        'total_cash': totals['total_cash'] or Decimal('0.00'),
        'total_upi': totals['total_upi'] or Decimal('0.00'),
        'total_card': totals['total_card'] or Decimal('0.00'),
        'total_pending': totals['total_pending'] or Decimal('0.00'),

        'credit_total_grand':total_credits['credit_total_grand'] or Decimal('0.00'),
    }

    return render(request, 'retail_sales_list.html', context)

@login_required
def retail_sales_delete(request, pk):
    if request.user.role not in ['super_admin', 'admin']:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    sale = get_object_or_404(RetailSales, pk=pk, delete_status=False)

    try:
        with transaction.atomic():
            # CORRECT: related_name='details'
            for detail in sale.details.all():
                item = detail.item
                if item.category.is_weight_based:
                    item.stock += detail.net_weight
                else:
                    item.stock += detail.qty
                item.save()

            sale.delete_status = True
            sale.deleted_by = request.user
            sale.save()

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def wholesale_sales_list(request):
    is_admin_like = request.user.role in ['super_admin', 'admin']
    
    branch_id_raw = request.GET.get('branch')        # "", "1", None
    from_date_str = request.GET.get('from_date')
    to_date_str   = request.GET.get('to_date')

    today = date.today()

    from_date_display = from_date_str or today.strftime('%Y-%m-%d')
    to_date_display   = to_date_str   or today.strftime('%Y-%m-%d')

    try:
        from_date = datetime.strptime(from_date_display, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        from_date = today

    try:
        to_date = datetime.strptime(to_date_display, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        to_date = today

    selected_branch = None
    if branch_id_raw and branch_id_raw.isdigit():
        selected_branch = int(branch_id_raw)

    sales = WholesaleSales.objects.filter(
        delete_status=False,
        sales_date__gte=from_date,
        sales_date__lte=to_date
    ).select_related('branch', 'customer', 'added_by')

    sales = sales.annotate(balance=F('grand_total') - F('paid_amount'))

    if not is_admin_like:
        sales = sales.filter(branch=request.user.branch)
        selected_branch_name = request.user.branch.branch_name
    else:
        if selected_branch is not None:
            sales = sales.filter(branch_id=selected_branch)
        selected_branch_name = "All Branches"
        if selected_branch is not None:
            try:
                selected_branch_name = Branch.objects.get(branch_id=selected_branch).branch_name
            except Branch.DoesNotExist:
                selected_branch_name = "Unknown Branch"

    sales = sales.order_by('-sales_date')

    totals = sales.aggregate(
    total_subtotal = Sum('total'),
    total_discount = Sum('discount'),
    total_grand    = Sum('grand_total'),
   )

    # Context — exactly like retail
    context = {
        'sales': sales,
        'branches': Branch.objects.all() if is_admin_like else [],
        'is_admin_like': is_admin_like,
        'selected_branch': selected_branch,           # int or None
        'from_date_str': from_date_display,           # for <input>
        'to_date_str': to_date_display,               # for <input>
        'from_date': from_date,                       # real date → for |date filter
        'to_date': to_date,                           # real date → for |date filter
        'selected_branch_name': selected_branch_name,
        'today': today.strftime('%Y-%m-%d'),

        'total_subtotal': totals['total_subtotal'] or Decimal('0.00'),
        'total_discount': totals['total_discount'] or Decimal('0.00'),
        'total_grand': totals['total_grand'] or Decimal('0.00'),
    }
    return render(request, 'wholesale_sales_list.html', context)

@login_required
def wholesale_sales_add(request):
    is_admin_like = request.user.role in ['super_admin', 'admin']

    if request.method == "POST":
        customer_id = request.POST.get('customer_id')

        form = WholesaleSalesForm(request.POST, user=request.user)
        formset = WholesaleSalesDetailFormSet(request.POST)
        customer_form = CustomerDataForm(request.POST, require_customer=True)  # Mandatory

        if form.is_valid() and formset.is_valid() and customer_form.is_valid():
            receipt_no = form.cleaned_data['receipt_no'].strip().upper()

            # Unique receipt check
            if WholesaleSales.objects.filter(receipt_no__iexact=receipt_no,delete_status=False).exists():
                messages.error(request, f"Receipt No '{receipt_no}' already used!")
                return render(request, "wholesale_sales_add.html", {
                    'form': form, 'formset': formset, 'customer_form': customer_form,
                    'is_admin_like': is_admin_like
                })

            with transaction.atomic():
                # 1. First handle customer (MANDATORY)
                customer_data = customer_form.cleaned_data
                customer, created = get_or_create_customer(customer_data, customer_id)

                # CRITICAL FIX: Force wholesale flag
                if created or not customer.whole_sale:
                    customer.whole_sale = True
                    customer.save()

                # Update existing customer if fields changed
                if not created:
                    updated = False
                    for field, value in customer_data.items():
                        if value and getattr(customer, field, None) != value:
                            setattr(customer, field, value)
                            updated = True
                    if updated:
                        customer.save()

                # 2. Now create the sale object BUT DO NOT SAVE YET
                sales = form.save(commit=False)
                sales.added_by = request.user
                if not is_admin_like:
                    sales.branch = request.user.branch

                # CRITICAL: Assign customer BEFORE saving!
                sales.customer = customer

                # Now it's safe to save
                sales.save()

                # 3. Save formset items
                for detail_form in formset:
                    if detail_form.cleaned_data and not detail_form.cleaned_data.get('DELETE', False):
                        detail = detail_form.save(commit=False)
                        detail.sales = sales
                        detail.save()

                        item = detail.item
                        qty = detail.qty or 0
                        net_weight = detail.net_weight or 0

                        if item.category.is_weight_based:
                            if item.stock < net_weight:
                                messages.error(request, f"Low stock: {item.name} (Need {net_weight} kg)")
                                raise ValueError("Low stock")
                            item.stock -= net_weight
                        else:
                            if item.stock < qty:
                                messages.error(request, f"Low stock: {item.name} (Need {qty})")
                                raise ValueError("Low stock")
                            item.stock -= qty
                        item.save()

                messages.success(request, f"Wholesale Sale {receipt_no} created successfully!")
                return redirect('wholesale_receipt', pk=sales.pk)

        else:
            # Show form errors
            messages.error(request, "Please correct the errors below.")

    else:
        # GET request
        initial = {
            'sales_date': date.today(),
            'payment_mode': 'pending',
            'paid_amount': '0.00',
        }
        if not is_admin_like and request.user.branch:
            initial['branch'] = request.user.branch

        form = WholesaleSalesForm(initial=initial, user=request.user)
        formset = WholesaleSalesDetailFormSet(queryset=WholesaleSalesDetails.objects.none())
        customer_form = CustomerDataForm(require_customer=True)  # Always required

    return render(request, "wholesale_sales_add.html", {
        'form': form,
        'formset': formset,
        'customer_form': customer_form,
        'is_admin_like': is_admin_like,
    })

@login_required
def wholesale_receipt(request, pk):
    sale = get_object_or_404(WholesaleSales, pk=pk, delete_status=False)
    return render(request, 'wholesale_receipt.html', {'sale': sale})

@login_required
def wholesale_sales_delete(request, pk):
    if request.user.role not in ['super_admin', 'admin', 'manager']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    sale = get_object_or_404(WholesaleSales, pk=pk, delete_status=False)
    
    with transaction.atomic():
        for detail in sale.wholesalesalesdetails_set.all():
            item = detail.item
            if item.category.is_weight_based:
                item.stock += detail.net_weight
            else:
                item.stock += detail.qty
            item.save()

        sale.delete_status = True
        sale.deleted_by = request.user
        sale.save()

    return JsonResponse({'success': True})



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
            'wholesale_price': str(item.price_per_unit_wholesale),
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
            'wholesale_price': str(item.price_per_unit_wholesale),
            'is_weight_based': item.category.is_weight_based
        }
        return JsonResponse(data)
    except Item.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)

@require_GET
def search_customers(request):
    q = request.GET.get('q', '').strip()
    type_ = request.GET.get('type', 'name')  # 'name' or 'phone'
    context = request.GET.get('context', '')  # 'wholesale' or 'retail'

    # Base queryset - ALWAYS define first
    customers = Customer.objects.filter(delete_status=False)

    # Apply context filter
    if context == 'wholesale':
        customers = customers.filter(whole_sale=True)
    elif context == 'retail':
        customers = customers.filter(whole_sale=False)
    # Else: show all (fallback)

    # Apply search
    if q:
        if type_ == 'phone':
            customers = customers.filter(customer_phone__icontains=q)
        else:
            customers = customers.filter(customer_name__icontains=q)

    # Limit results for performance
    customers = customers[:20]

    data = [
        {
            'id': c.id,
            'name': c.customer_name or "Unnamed Customer",
            'phone': c.customer_phone or "",
            'address': c.customer_address or "",
            'gstin': c.gstin or ""
        }
        for c in customers
    ]
    return JsonResponse(data, safe=False)

@require_GET
def item_details(request, item_id):
    try:
        item = Item.objects.get(id=item_id)
        return JsonResponse({'is_weight_based': item.category.is_weight_based})
    except Item.DoesNotExist:
        return JsonResponse({'error': 'Item not found', 'is_weight_based': False}, status=404)
    
@login_required
def employe_add(request):
    if request.method == "POST":
        form = EmployeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Employe recorded successfully!")
            return redirect("employe_add")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = EmployeForm()

    return render(request, "employe_add.html", {"form": form})

from django.forms import inlineformset_factory

@login_required
def attendance_view(request):
    if request.user.role not in ['admin', 'super_admin']:
        messages.error(request, "You are not authorized.")
        return redirect('dashboard')

    today = date.today()
    date_str = request.GET.get('date', today.isoformat())
    branch_id = request.GET.get('branch')

    try:
        selected_date = date.fromisoformat(date_str)
    except ValueError:
        selected_date = today

    # BRANCH
    if not branch_id:
        return render(request, 'attendance.html', {
            'selected_date': selected_date,
            'branches': Branch.objects.all(),
            'today': today,
            'no_branch_selected': True,
        })

    branch = get_object_or_404(Branch, branch_id=int(branch_id))

    # EMPLOYEES
    employees = Employe.objects.filter(
        delete_status=False,
        role__in=['staff', 'manager'],
        branch=branch
    ).order_by('name')

    if not employees.exists():
        return render(request, 'attendance.html', {
            'selected_date': selected_date,
            'branches': Branch.objects.all(),
            'selected_branch_id': branch_id,
            'selected_branch': branch,
            'today': today,
            'no_employees': True,
        })

    # GET: Build forms
    if request.method == 'GET':
        forms = []
        existing = Attendance.objects.filter(
            employee__in=employees,
            date=selected_date
        ).select_related('recorded_by')

        saved_map = {a.employee_id: a.status for a in existing}
        already_saved = len(saved_map) == employees.count()

        for emp in employees:
            instance = next((a for a in existing if a.employee_id == emp.id), None)
            form = AttendanceInlineForm(
                instance=instance,
                initial={'status': 'present'} if not instance else None,
                prefix=f'emp-{emp.id}'
            )
            if already_saved:
                form.fields['status'].disabled = True
            forms.append((emp, form))

        context = {
            'forms': forms,
            'selected_date': selected_date,
            'branches': Branch.objects.all(),
            'selected_branch_id': branch_id,
            'selected_branch': branch,
            'today': today,
            'already_saved': already_saved,
            'saved_on': existing.first().recorded_at if already_saved and existing else None,
            'recorded_by': existing.first().recorded_by if already_saved and existing else None,
        }
        return render(request, 'attendance.html', context)

    # POST: Save
    if request.method == 'POST':
        forms = []
        all_valid = True

        for emp in employees:
            prefix = f'emp-{emp.id}'
            form = AttendanceInlineForm(request.POST, instance=None, prefix=prefix)
            forms.append((emp, form))
            if not form.is_valid():
                all_valid = False

        if not all_valid:
            messages.error(request, "Please select attendance for all employees.")
            context = {
                'forms': forms,
                'selected_date': selected_date,
                'branches': Branch.objects.all(),
                'selected_branch_id': branch_id,
                'selected_branch': branch,
                'today': today,
            }
            return render(request, 'attendance.html', context)

        with transaction.atomic():
            for emp, form in forms:
                status = form.cleaned_data['status']
                Attendance.objects.update_or_create(
                    employee=emp,
                    date=selected_date,
                    defaults={
                        'status': status,
                        'branch': branch,
                        'recorded_by': request.user
                    }
                )

        messages.success(request, f"Attendance saved for {selected_date}")
        return redirect(request.path + f'?date={selected_date}&branch={branch_id}')
    
@require_GET
def check_receipt(request):
    receipt_no = request.GET.get('receipt_no', '').strip()
    type_ = request.GET.get('type', 'retail')
    
    if type_ == 'wholesale':
        exists = WholesaleSales.objects.filter(receipt_no__iexact=receipt_no).exists()
    else:
        exists = RetailSales.objects.filter(receipt_no__iexact=receipt_no).exists()
    
    return JsonResponse({'exists': exists})
