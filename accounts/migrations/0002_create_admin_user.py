from django.db import migrations
from django.contrib.auth.models import User

def create_admin_user(apps, schema_editor):
    User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123!'  # Remplacez par un mot de passe sécurisé
    )

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),  # Assurez-vous que la dépendance est correcte
    ]

    operations = [
        migrations.RunPython(create_admin_user),
    ]