from django.urls import path
from .views import login_view
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('login/', login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logout/', views.user_logout, name='logout'),

    # Supplier URLs
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.supplier_add, name='supplier_add'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),
    path('update/<int:pk>/', views.supplier_update, name='supplier_update'),

    #supplier payment URLs
    path('supplier_payment/add/', views.supplier_pay, name='supplier_pay'),
    path('supplier-payments/', views.supplier_payment_list, name='supplier_payment_list'),
    path('supplier-payments/<int:pk>/update/', views.supplier_payment_update, name='supplier_payment_update'),
    path('supplier-payments/<int:pk>/delete/', views.supplier_payment_delete, name='supplier_payment_delete'),

    # Branch URLs
    path('branch_list/', views.branch_list, name='branch_list'),
    path('branch_add/', views.branch_add, name='branch_add'),
    path('branch_delete/<int:pk>/', views.branch_delete, name='branch_delete'),
    path('branch_update/<int:pk>/', views.branch_update, name='branch_update'),

    # Item Category URLs
    path('category_list/', views.item_category_list, name='category_list'),
    path('category_add/', views.item_category_add, name='category_add'),
    path('category_delete/<int:pk>/', views.item_category_delete, name='category_delete'),
    path('category_update/<int:pk>/', views.item_category_update, name='category_update'),  

    # Items URLs 
    path('item_add/', views.item_add, name='item_add'),
    path('item_list/', views.item_list, name='item_list'),
    path('item_delete/<int:pk>/', views.item_delete, name='item_delete'),
    path('item_update/<int:pk>/', views.item_update, name='item_update'),  


    # Purchase URLs
    path('purchase/add/', views.purchase_add, name='purchase_add'),
    path('purchases/', views.purchase_list, name='purchase_list'),
    path('purchases/view/<int:pk>/', views.purchase_view, name='purchase_view'),
    path('purchases/delete/<int:pk>/', views.purchase_delete, name='purchase_delete'),

    # Retail Sales URLs
    path('retailsales/add/', views.retail_sales_add, name='retail_sales_add'),
    path('sales/retail/list/', views.retail_sales_list, name='retail_sales_list'),
    path('sales/retail/receipt/<int:pk>/', views.retail_receipt, name='retail_receipt'),
    path('sales/retail/delete/<int:pk>/', views.retail_sales_delete, name='retail_sales_delete'),
    path('sales/retail/pay-credit/<int:pk>/', views.retail_pay_credit, name='retail_pay_credit'),

    

    # Wholesale Sales URLs
    path('wholesale-sales/add/', views.wholesale_sales_add, name='wholesale_sales_add'),
    path('sales/wholesale/list/', views.wholesale_sales_list, name='wholesale_sales_list'),
    path('sales/wholesale/receipt/<int:pk>/', views.wholesale_receipt, name='wholesale_receipt'),
    path('sales/wholesale/delete/<int:pk>/', views.wholesale_sales_delete, name='wholesale_sales_delete'),
    path('api/check_receipt/', views.check_receipt, name='check_receipt'),

    # Employe URLs
    path('employe/add/', views.employe_add, name='employe_add'),
    path('attendance/', views.attendance_view, name='attendance'),

    #api URL
    path('api/items-by-category/<int:category_id>/', views.items_by_category, name='items_by_category'),
    path('api/category-details/<int:category_id>/', views.category_details, name='category_details'),
    path('api/search_items/', views.search_items, name='search_items'),
    path('api/item_by_code/', views.item_by_code, name='item_by_code'),
    path('api/search_customers/', views.search_customers, name='search_customers'),
    path('api/item-details/<int:item_id>/', views.item_details, name='item_details'),

    path('customers/', views.customer_list, name='customer_list'),
    path('customers/add/', views.customer_add, name='customer_add'),
    path('customers/update/<int:pk>/', views.customer_update, name='customer_update'),
    path('customers/delete/<int:pk>/', views.customer_delete, name='customer_delete'),
    
    # Expense URLs
    path('expense-categories/', views.expense_category_list, name='expense_category_list'),
    path('expense-categories/add/', views.expense_category_add, name='expense_category_add'),
    path('expense-categories/<int:pk>/update/', views.expense_category_update, name='expense_category_update'),
    path('expense-categories/<int:pk>/delete/', views.expense_category_delete, name='expense_category_delete'),

    path('expenses/add/', views.expense_add, name='expense_add'),
    path('expenses/', views.expense_list, name='expense_list'),

    #create login
    # urls.py
    path('employee-login/create/', views.employee_login_create, name='employee_login_create'),

    #Reports
    path('retail-item-report/', views.retail_item_report, name='retail_item_report'),
    path('wholesale-item-report/', views.wholesale_item_report, name='wholesale_item_report'),
    path('wholesale-payments/', views.wholesale_payment_list, name='wholesale_payment_list'),

    path('wholesale-payment/add/', views.wholesale_payment_add, name='wholesale_payment_add'),
    
]

