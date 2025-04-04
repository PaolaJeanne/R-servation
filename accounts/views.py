from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db.models import Sum, Count,Q
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import PermissionDenied
from transport.models import Reservation, Transport,Payment
from .forms import SignUpForm, LoginForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.conf import settings


User = get_user_model()

def acceuil_view(request):
    """Vue pour la page d'accueil"""
    return render(request, 'accounts/acceuil.html')

@csrf_exempt
def user_logout(request):
    logout(request)
    messages.success(request, "Vous avez été déconnecté avec succès.")
    return redirect('accounts:login')  # Redirige vers la page de connexion

@csrf_exempt
def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.email = form.cleaned_data['email'].lower()
                user.first_name = form.cleaned_data['first_name']
                user.last_name = form.cleaned_data['last_name']
                user.save()
                
                profile = user.profile
                profile.phone_number = form.cleaned_data['phone_number']
                
                if 'photo' in request.FILES:
                    profile.photo = request.FILES['photo']
                
                profile.is_admin = form.cleaned_data.get('is_admin', False)
                profile.save()
                
                messages.success(request, "Inscription réussie ! Veuillez vous connecter.")
                return redirect('accounts:login')
            
            except Exception as e:
                messages.error(request, f"Erreur lors de l'inscription : {str(e)}")
                print(f"Erreur inscription: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = SignUpForm()
    
    return render(request, 'accounts/signup.html', {'form': form})

@csrf_exempt
def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, "Connexion réussie.")
                
                if hasattr(user, 'profile') and user.profile.is_admin:
                    return redirect('accounts:admin_dashboard')  # Redirige vers le tableau de bord admin
                return redirect('transport:transport_list')  # Assurez-vous que cela existe
            else:
                messages.error(request, 'Identifiants invalides')
        else:
            messages.error(request, 'Veuillez corriger les erreurs')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})



@login_required
def admin_dashboard(request):
    if not request.user.profile.is_admin:
        raise PermissionDenied

    ITEMS_PER_PAGE = 6
    
    # Récupération des paramètres avec valeurs par défaut
    transport_type = request.GET.get('type', '')
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    transport_page = request.GET.get('page_transports', 1)
    reservation_page = request.GET.get('page_reservations', 1)

    # Construction des URLs de pagination
    def get_transport_pagination_url(page):
        params = []
        if transport_type:
            params.append(f'type={transport_type}')
        if search_query:
            params.append(f'q={search_query}')
        return f"?page_transports={page}&{'&'.join(params)}" if params else f"?page_transports={page}"

    def get_reservation_pagination_url(page):
        return f"?page_reservations={page}&status={status_filter}" if status_filter else f"?page_reservations={page}"

    # Query transports
    transports = Transport.objects.all().order_by('-departure_time')
    if transport_type:
        transports = transports.filter(type=transport_type)
    if search_query:
        transports = transports.filter(
            Q(name__icontains=search_query) |
            Q(departure_city__icontains=search_query) |
            Q(arrival_city__icontains=search_query)
        )
    
    transport_paginator = Paginator(transports, ITEMS_PER_PAGE)
    try:
        transports_page = transport_paginator.page(transport_page)
    except PageNotAnInteger:
        transports_page = transport_paginator.page(1)
    except EmptyPage:
        transports_page = transport_paginator.page(transport_paginator.num_pages)

    # Query reservations
    reservations = Reservation.objects.select_related('transport', 'client').order_by('-reservation_date')
    if status_filter:
        reservations = reservations.filter(status=status_filter)
    
    reservation_paginator = Paginator(reservations, ITEMS_PER_PAGE)
    try:
        reservations_page = reservation_paginator.page(reservation_page)
    except PageNotAnInteger:
        reservations_page = reservation_paginator.page(1)
    except EmptyPage:
        reservations_page = reservation_paginator.page(reservation_paginator.num_pages)

    # Stats
    stats = {
        'transports_count': transports.count(),
        'reservations_count': reservations.count(),
        'total_users': User.objects.count(),
        'revenue': Payment.objects.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or 0,
    }

    context = {
        'transports': transports_page,
        'reservations': reservations_page,
        'transport_types': Transport.TRANSPORT_TYPES,
        'status_choices': Reservation.RESERVATION_STATUS,
        'selected_type': transport_type,
        'selected_status': status_filter,
        'search_query': search_query,
        'stats': stats,
        'online_users': User.objects.filter(last_login__gte=timezone.now()-timedelta(minutes=15)).count(),
        'get_transport_pagination_url': get_transport_pagination_url,
        'get_reservation_pagination_url': get_reservation_pagination_url,
    }
    
    return render(request, 'transport/admin_dashboard.html', context)