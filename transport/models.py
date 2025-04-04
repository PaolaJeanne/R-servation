from datetime import timezone
from decimal import Decimal
from venv import logger
from django.db import models, transaction
from django.db.models import F
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.forms import ValidationError

class Transport(models.Model):
    TRANSPORT_TYPES = [
        ('minibus', 'Minibus'),
        ('microbus', 'Microbus'),
        ('standard_bus', 'Bus standard'),
        ('coach_bus', 'Bus grand tourisme'),
        ('articulated_bus', 'Bus articulé'),
        ('double_decker', 'Bus à étage'),
        ('autre', 'Autre type de bus'),
    ]
    TRANSPORT_CLASSES = [
        ('commun', 'Commun'),
        ('vip', 'VIP'),
        ('luxe', 'Luxe'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField()
    type = models.CharField(max_length=20, choices=TRANSPORT_TYPES, default='minibus')
    classe = models.CharField(max_length=10, choices=TRANSPORT_CLASSES, default='commun')
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    available_seats = models.PositiveIntegerField(default=0)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    departure_city = models.CharField(max_length=100)
    arrival_city = models.CharField(max_length=100)
    

    class Meta:
        ordering = ['departure_time']
        verbose_name = "Transport"
        verbose_name_plural = "Transports"

    def __str__(self):
        return f"{self.get_type_display()} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.available_seats:
            self.available_seats = self.capacity
        super().save(*args, **kwargs)

    def clean(self):
        """Validation personnalisée pour le transport"""
        if self.arrival_time and self.departure_time:
            if self.arrival_time <= self.departure_time:
                raise ValidationError("L'heure d'arrivée doit être après l'heure de départ.")
        super().clean()
        
class Reservation(models.Model):
    RESERVATION_STATUS = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmée'),
        ('cancelled', 'Annulée'),
    ]

    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations')
    transport = models.ForeignKey(Transport, on_delete=models.PROTECT, related_name='reservations')
    reservation_date = models.DateTimeField(auto_now_add=True)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    number_of_seats = models.PositiveIntegerField(validators=[MinValueValidator(1)], help_text="Nombre de places réservées (minimum 1)")
    updated_at = models.DateTimeField(auto_now=True)
    passenger_names = models.TextField()
    status = models.CharField(max_length=10, choices=RESERVATION_STATUS, default='pending')
    payment_reference = models.CharField(max_length=50, blank=True, null=True)
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-reservation_date']
        verbose_name = "Réservation"
        verbose_name_plural = "Réservations"

    def __str__(self):
        return f"Réservation #{self.id} - {self.client.username}"

    @property
    def is_paid(self):
        return hasattr(self, 'payment') and self.payment.status == 'completed'

    @property
    def total_amount(self):
        """Retourne le montant total (propriété seulement)"""
        if self.total_price is not None:
            return self.total_price
        return Decimal(self.number_of_seats) * self.transport.price

    def clean(self):
        """Validation personnalisée pour la réservation"""
        if self.arrival_time and self.departure_time:
            if self.arrival_time <= self.departure_time:
                raise ValidationError("L'heure d'arrivée doit être après l'heure de départ.")
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def cancel(self):
        """Annulation atomique de la réservation"""
        if self.status == 'cancelled':
            return False

        try:
            with transaction.atomic():
                # Version optimiste de la mise à jour
                updated = Transport.objects.filter(
                    id=self.transport.id
                ).update(
                    available_seats=F('available_seats') + self.number_of_seats
                )

                if not updated:
                    raise ValueError("Échec de la mise à jour du transport")

                self.status = 'cancelled'
                self.save(update_fields=['status', 'updated_at'])
                return True

        except Exception as e:
            logger.error(f"Échec de l'annulation de la réservation {self.id}: {str(e)}")
            return False

class Payment(models.Model):
    PAYMENT_METHODS = [
        ('orange', 'Orange Money'),
        ('mtn', 'MTN Mobile Money'),
        ('visa', 'Visa'),
        ('mastercard', 'MasterCard'),
        ('wave', 'Wave'),
    ]

    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('completed', 'Terminé'),
        ('failed', 'Échoué'),
    ]

    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.CASCADE,
        related_name='payment'
    )
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"

    def __str__(self):
        return f"Paiement #{self.id} ({self.get_method_display()})"