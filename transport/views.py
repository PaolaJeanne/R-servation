
from decimal import Decimal
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Payment, Reservation, Transport
from .forms import ReservationForm, TransportForm
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def transport_list(request):
    transports = Transport.objects.filter(
        available_seats__gt=0,
        departure_time__gte=timezone.now()
    ).order_by('departure_time')

    transport_type = request.GET.get('type')
    if transport_type:
        transports = transports.filter(type=transport_type)

    transport_classe = request.GET.get('classe')
    if transport_classe:
        transports = transports.filter(classe=transport_classe)

    paginator = Paginator(transports, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'type_choices': Transport.TRANSPORT_TYPES,
        'classe_choices': Transport.TRANSPORT_CLASSES,
        'selected_type': transport_type or '',
        'selected_classe': transport_classe or '',
    }
    return render(request, 'transport/transport_list.html', context)

@login_required
def transport_detail(request, transport_id):
    transport = get_object_or_404(Transport, id=transport_id)
    can_reserve = transport.available_seats > 0

    return render(request, 'transport/transport_detail.html', {
        'transport': transport,
        'can_reserve': can_reserve
    })

@login_required  
@transaction.atomic  
def reserve_transport(request, transport_id):  
    transport = get_object_or_404(Transport, id=transport_id)
    
    if transport.available_seats <= 0:
        messages.error(request, "Ce transport est complet.")
        return redirect('transport:transport_detail', transport_id=transport.id)
    
    if request.method == 'POST':  
        form = ReservationForm(request.POST)
        if form.is_valid():  
            try:
                reservation = form.save(commit=False)
                reservation.client = request.user
                reservation.transport = transport
                reservation.status = 'pendding'  # Utilisation de la constante
                reservation.departure_time = transport.departure_time  
                reservation.arrival_time = transport.arrival_time
                
                # Calcul MANUEL du prix avant sauvegarde
                reservation.total_price = Decimal(reservation.number_of_seats) * transport.price

                if reservation.number_of_seats > transport.available_seats:
                    messages.error(request, f"Seulement {transport.available_seats} places disponibles")
                    return redirect('transport:reserve_transport', transport_id=transport.id)

                with transaction.atomic():
                    reservation.save()  # Appellera save() du modèle
                    transport.available_seats -= reservation.number_of_seats
                    transport.save()

                messages.success(request, "Réservation créée avec succès!")
                return redirect('transport:create_payment', reservation_id=reservation.id)

            except Exception as e:
                messages.error(request, f"Erreur lors de la création: {str(e)}")
        else:
            for field, errors in form.errors.items():
                messages.error(request, f"{field}: {', '.join(errors)}")
    else:
        form = ReservationForm(initial={
            'number_of_seats': 1,
            'passenger_names': request.user.get_full_name() or request.user.username
        })

    return render(request, 'transport/reserve_transport.html', {
        'transport': transport,
        'form': form,
        'can_reserve': transport.available_seats > 0
    })

@login_required
def reservation_detail(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, client=request.user)
    return render(request, 'transport/reservation_detail.html', {
        'reservation': reservation
    })

@login_required
@transaction.atomic
def update_reservation(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, client=request.user)
    transport = reservation.transport

    if request.method == 'POST':
        form = ReservationForm(request.POST, instance=reservation, transport=transport)
        if form.is_valid():
            old_seats = reservation.number_of_seats
            new_reservation = form.save(commit=False)
            new_seats = new_reservation.number_of_seats
            seat_diff = new_seats - old_seats

            if seat_diff > 0 and seat_diff > transport.available_seats:
                messages.error(request, f"Nombre de places insuffisant. Il reste seulement {transport.available_seats} place(s).")
                return render(request, 'transport/update_reservation.html', {
                    'form': form,
                    'reservation': reservation
                })

            # Mettre à jour le nombre de places dans le transport
            transport.available_seats -= seat_diff
            transport.save()

            new_reservation.total_price = new_seats * transport.price
            new_reservation.save()

            messages.success(request, "La réservation a été mise à jour avec succès.")
            return redirect('transport:my_reservations')
    else:
        form = ReservationForm(instance=reservation, transport=transport)

    return render(request, 'transport/update_reservation.html', {
        'form': form,
        'reservation': reservation
    })

@login_required
@transaction.atomic
def cancel_reservation(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, client=request.user)

    if reservation.status == 'cancel':  # Utilisation de la constante
        messages.warning(request, "Cette réservation a déjà été annulée.")
        return redirect('transport:my_reservations')

    if request.method == 'POST':
        if reservation.cancel():
            messages.success(request, "Réservation annulée avec succès.")
        else:
            messages.error(request, "Échec de l'annulation de la réservation. Veuillez réessayer.")
        return redirect('transport:my_reservations')

    return render(request, 'transport/cancel_reservation.html', {
        'reservation': reservation
    })

@login_required
def create_payment(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    return render(request, 'transport/create_payment.html', {
        'reservation': reservation,
        'total_amount': reservation.total_price
    })

@login_required
def process_payment(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, client=request.user)

    # Vérifier si un paiement existe déjà pour cette réservation
    if hasattr(reservation, 'payment') and reservation.payment.status == 'completed':
        messages.error(request, 'Un paiement a déjà été effectué pour cette réservation.')
        return redirect('transport:my_reservations')

    # Si le formulaire est soumis (POST)
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')

        # Vérifier si la méthode de paiement est valide
        if payment_method not in dict(Payment.PAYMENT_METHODS).keys():
            messages.error(request, 'Méthode de paiement invalide.')
            return redirect('transport:process_payment', reservation_id=reservation.id)

        # Créer un objet Payment pour la réservation si aucun paiement n'a été effectué
        if not hasattr(reservation, 'payment'):
            payment = Payment.objects.create(
                reservation=reservation,
                method=payment_method,
                amount=reservation.total_price,
                status='pending'  # Initialement en attente
            )
        else:
            # Si un paiement existe, vous pouvez le mettre à jour si nécessaire
            payment = reservation.payment
            payment.method = payment_method
            payment.amount = reservation.total_price
            payment.status = 'pending'
            payment.save()

        # Simulation du paiement (ici vous pouvez intégrer avec un service réel comme Stripe, etc.)
        payment.status = 'completed'  # Paiement validé
        payment.save()

        # Mise à jour du statut de la réservation après le paiement
        reservation.status = 'confirmed'  # La réservation est maintenant confirmée
        reservation.save()

        messages.success(request, 'Paiement effectué avec succès et réservation confirmée.')
        return redirect('transport:payment_success', reservation_id=reservation.id)  
    return render(request, 'transport/process_payment.html', {'reservation': reservation})

   

@login_required
def payment_success(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    payment = get_object_or_404(Payment, reservation=reservation)
    return render(request, 'transport/payment_success.html', {
        'reservation': reservation,
        'payment': payment
    })

@login_required
def payment_cancel(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    return render(request, 'transport/payment_cancel.html', {
        'reservation': reservation
    })

@login_required
def my_reservations(request):
    reservations = request.user.reservations.exclude(status='pendding').select_related('transport')
    
    # Actualiser les statuts des réservations
    for reservation in reservations:
        reservation.refresh_from_db()

    return render(request, 'transport/my_reservation.html', {
        'reservations': reservations,
        'now': timezone.now()
    })


def add_transport(request):
    if request.method == 'POST':
        form = TransportForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Transport ajouté avec succès.")
        return redirect('accounts:admin_dashboard')
    else:
        form = TransportForm()
    
    return render(request, 'transport/add_transport.html', {'form': form})

def edit_transport(request, id):
    transport = get_object_or_404(Transport, id=id)
    
    if request.method == 'POST':
        form = TransportForm(request.POST, instance=transport)
        if form.is_valid():
            form.save()
            messages.success(request, "Transport mis à jour avec succès.")
        return redirect('accounts:admin_dashboard')
    else:
        form = TransportForm(instance=transport)
    
    return render(request, 'transport/edit_transport.html', {'form': form, 'transport': transport})

def delete_transport(request, id):
    transport = get_object_or_404(Transport, id=id)
    
    if request.method == 'POST':
        transport.delete()
        messages.success(request, "Transport supprimé avec succès.")
        return redirect('accounts:admin_dashboard')
    
    return render(request, 'transport/delete_transport.html', {'transport': transport})