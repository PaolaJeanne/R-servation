from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Transport, Reservation, Payment
from .forms import ReservationForm


@login_required
def transport_list(request):
    transports = Transport.objects.all().order_by('departure_time')
    
    # Pagination
    paginator = Paginator(transports, 6)  # Afficher 6 transports par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'type_choices': Transport.TRANSPORT_TYPES,
        'classe_choices': Transport.TRANSPORT_CLASSES,
        'selected_type': request.GET.get('type', ''),
        'selected_classe': request.GET.get('classe', ''),
    }
    return render(request, 'transport/transport_list.html', context)

@login_required
def transport_detail(request, transport_id):
    transport = get_object_or_404(Transport, id=transport_id)
    return render(request, 'transport/transport_detail.html', {
        'transport': transport,
        'can_reserve': transport.available_seats > 0
    })

@login_required  
def reserve_transport(request, transport_id):  
    transport = get_object_or_404(Transport, id=transport_id)
    
    if request.method == 'POST':  
        form = ReservationForm(request.POST)
        if form.is_valid():  
            reservation = form.save(commit=False)
            reservation.client = request.user
            reservation.transport = transport
            reservation.total_price = reservation.number_of_seats * transport.price
            
            # Check available seats
            if reservation.number_of_seats > transport.available_seats:
                messages.error(request, f"Seulement {transport.available_seats} places disponibles.")
                return redirect('transport:reserve_transport', transport_id=transport.id)

            reservation.save()

            transport.available_seats -= reservation.number_of_seats
            transport.save()

            messages.success(request, "Réservation créée avec succès!")
            return redirect('transport:create_payment', reservation_id=reservation.id)
    else:
        form = ReservationForm()

    return render(request, 'transport/reserve_transport.html', {
        'transport': transport,
        'form': form,
    })


@login_required
def reservation_detail(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, client=request.user)
    return render(request, 'transport/reservation_detail.html', {
        'reservation': reservation
    })
    
    
@login_required
def update_reservation(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, client=request.user)
    if request.method == 'POST':
        form = ReservationForm(request.POST, instance=reservation)
        if form.is_valid():
            form.save()
            messages.success(request, "La réservation a été mise à jour avec succès.")
            return redirect('transport:my_reservations')
    else:
        form = ReservationForm(instance=reservation)

    return render(request, 'transport/update_reservation.html', {
        'form': form,
        'reservation': reservation
    })
    
    
@login_required
def cancel_reservation(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, client=request.user)

    if request.method == 'POST':
        if reservation.cancel():
            messages.success(request, "Réservation annulée avec succès.")
            return redirect('transport:my_reservations')
        else:
            messages.error(request, "Échec de l'annulation de la réservation.")
    return render(request, 'transport/cancel_reservation.html', {
        'reservation': reservation
    })
    
    
@login_required
def create_payment(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    return render(request, 'transport/create_payment.html', {
        'reservation': reservation,
        'total_amount': reservation.total_amount
    })

@require_POST
def process_payment(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, client=request.user)
    payment_method = request.POST.get('payment_method')

    if payment_method not in ['orange', 'mtn', 'paypal']:
        messages.error(request, "Méthode de paiement non valide.")
        return redirect('transport:create_payment', reservation_id=reservation.id)

    try:
        # Simuler le processus de paiement
        payment = Payment.objects.create(
            reservation=reservation,
            method=payment_method,
            amount=reservation.total_amount,
            status='completed'
        )
        
        reservation.status = 'confirmed'
        reservation.save()

        messages.success(request, "Paiement réussi!")
        return redirect('transport:payment_success', reservation_id=reservation.id)

    except Exception as e:
        messages.error(request, f"Erreur lors du paiement: {str(e)}")
        return redirect('transport:payment_cancel', reservation_id=reservation.id)

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
    reservations = request.user.reservations.exclude(status='cancelled').select_related('transport')
    return render(request, 'transport/my_reservations.html', {
        'reservations': reservations,
    })