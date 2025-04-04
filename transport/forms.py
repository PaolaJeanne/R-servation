from django import forms
from .models import Reservation

class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['number_of_seats', 'passenger_names']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['number_of_seats'].widget.attrs.update({
            'min': 1,
            'class': 'form-control',
            'type': 'number'  # Assure que le champ est un input de type number
        })
        self.fields['passenger_names'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Noms des passagers (séparés par des virgules)'
        })
    
    def clean_number_of_seats(self):
        seats = self.cleaned_data.get('number_of_seats')
        if seats is None or seats < 1:
            raise forms.ValidationError("Le nombre de places doit être au moins 1")
        return seats
    
    
from .models import Transport

class TransportForm(forms.ModelForm):
    class Meta:
        model = Transport
        fields = ['name', 'description', 'type', 'classe', 'capacity', 'available_seats', 'departure_city', 'arrival_city', 'departure_time', 'arrival_time', 'price']