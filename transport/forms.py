import logging
from django import forms
from transport.models import Reservation, Transport
from django.core.exceptions import ValidationError


class ReservationForm(forms.ModelForm):
    passenger_names = forms.CharField(
        required=False,
        label='Noms des passagers',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex : Alice, Bob, Charlie'
        })
    )

    class Meta:
        model = Reservation
        fields = ['number_of_seats', 'passenger_names']

        widgets = {
            'number_of_seats': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'Ex : 2'
            }),
        }

    class Meta:
        model = Reservation
        fields = ['number_of_seats']

    def __init__(self, *args, **kwargs):
        self.transport = kwargs.pop('transport', None)
        super().__init__(*args, **kwargs)

    def clean_number_of_seats(self):
        number_of_seats = self.cleaned_data.get('number_of_seats')
        if self.transport and number_of_seats > self.transport.available_seats:
            raise forms.ValidationError("Nombre de places demandées supérieur au nombre de places disponibles.")
        return number_of_seats


class TransportForm(forms.ModelForm):
    class Meta:
        model = Transport
        fields = ['name', 'description', 'type', 'classe', 'capacity', 'available_seats',
                  'departure_city', 'arrival_city', 'departure_time', 'arrival_time', 'price']
