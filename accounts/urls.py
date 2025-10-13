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

    # Retail Sales URLs
    path('sales/add/', views.retail_sales_add, name='retail_sales_add'),

    #api URL
    path('api/items-by-category/<int:category_id>/', views.items_by_category, name='items_by_category'),
    path('api/category-details/<int:category_id>/', views.category_details, name='category_details'),
    path('api/search_items/', views.search_items, name='search_items'),
    path('api/item_by_code/', views.item_by_code, name='item_by_code'),
    path('api/search_customers/', views.search_customers, name='search_customers'),
    path('api/item-details/<int:item_id>/', views.item_details, name='item_details'),
]
