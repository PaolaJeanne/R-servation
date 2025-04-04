from django.urls import path
from . import views


app_name = 'accounts'


urlpatterns = [
    path('acceuil/', views.acceuil_view, name='acceuil'),  # Optionnel
    path('signup/', views.signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
]