from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth import get_user_model
from .forms import SignUpForm, LoginForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import PermissionDenied

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
                    return redirect('accounts:admin_dashboard')  # Corrected here
                return redirect('transport:transport_list')  # Ensure this exists
            else:
                messages.error(request, 'Identifiants invalides')
        else:
            messages.error(request, 'Veuillez corriger les erreurs')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


@login_required(login_url='accounts:login')
def admin_dashboard(request):
    if not request.user.profile.is_admin:
        raise PermissionDenied
    return render(request, 'transport/admin_dashboard.html')



