from django.urls import path
from . import views

app_name = 'transport'

urlpatterns = [
    path('', views.transport_list, name='transport_list'),
    path('transport/<int:transport_id>/', views.transport_detail, name='transport_detail'),
    path('reserve/<int:transport_id>/', views.reserve_transport, name='reserve_transport'),
    path('reservation/<int:reservation_id>/', views.reservation_detail, name='reservation_detail'),
    path('payment/<int:reservation_id>/', views.create_payment, name='create_payment'),
    path('payment/<int:reservation_id>/process/', views.process_payment, name='process_payment'),
    path('payment/<int:reservation_id>/success/', views.payment_success, name='payment_success'),
    path('payment/<int:reservation_id>/cancel/', views.payment_cancel, name='payment_cancel'),
    path('my-reservations/', views.my_reservations, name='my_reservations'),
    path('update-reservation/<int:reservation_id>/', views.update_reservation, name='update_reservation'),
    path('cancel-reservation/<int:reservation_id>/', views.cancel_reservation, name='cancel_reservation'),
    path('admin/transport/add/', views.add_transport, name='add_transport'),  # Ajoutez cette ligne
    path('admin/transport/edit/<int:id>/', views.edit_transport, name='edit_transport'),
    path('admin/transport/delete/<int:id>/', views.delete_transport, name='delete_transport'),
]