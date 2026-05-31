# django_configs/urls.py
# Paste this file or add these routes inside your Django app's urls.py.

from django.urls import path
from . import views

urlpatterns = [
    # Discover View / Home Page (as '/' mapped to find_workers)
    path('', views.find_workers, name='find_workers'),
    path('bookings/', views.my_bookings, name='my_bookings'),
    path('contact/', views.contact, name='contact'),
    
    # Auth Views
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    
    # Worker Views
    path('become-worker/', views.become_worker, name='become_worker'),
    path('worker/dashboard/', views.worker_dashboard, name='worker_dashboard'),
    path('worker/edit/', views.worker_profile_edit, name='worker_profile_edit'),
    path('worker/<str:worker_id>/', views.worker_detail, name='worker_detail'),
    
    # Admin Views
    path('admin-panel/overview/', views.admin_overview, name='admin_overview'),
    path('admin-panel/users/', views.admin_users, name='admin_users'),
    path('admin-panel/workers/', views.admin_workers, name='admin_workers'),
    path('admin-panel/bookings/', views.admin_bookings, name='admin_bookings'),
]
