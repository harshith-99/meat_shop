from django.contrib import admin
from django.urls import path, include
from accounts import views as accounts_views
from django.shortcuts import redirect

def redirect_to_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('', redirect_to_login),
]

