# Generated by Django 4.2.16 on 2024-09-17 23:54

import core.models.base_model
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Address",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "address_type",
                    models.CharField(
                        choices=[
                            ("Billing", "Billing"),
                            ("Shipping", "Shipping"),
                            ("Other", "Other"),
                        ],
                        default="Other",
                        max_length=20,
                    ),
                ),
                ("line1", models.CharField(max_length=255)),
                ("line2", models.CharField(blank=True, max_length=255, null=True)),
                ("city", models.CharField(max_length=100)),
                ("state", models.CharField(max_length=100)),
                ("postal_code", models.CharField(max_length=20)),
                ("country", models.CharField(max_length=100)),
            ],
            options={
                "ordering": ["-created_at"],
                "abstract": False,
            },
            bases=(core.models.base_model.JSONSerializableMixin, models.Model),
        ),
        migrations.CreateModel(
            name="PromoCode",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=50, unique=True)),
                ("discount_percentage", models.FloatField()),
                ("valid_from", models.DateTimeField()),
                ("valid_to", models.DateTimeField()),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ["-created_at"],
                "abstract": False,
            },
            bases=(core.models.base_model.JSONSerializableMixin, models.Model),
        ),
        migrations.CreateModel(
            name="SubscriptionPlan",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "name",
                    models.CharField(
                        choices=[
                            ("Free", "Free"),
                            ("Standard", "Standard"),
                            ("Premium", "Premium"),
                        ],
                        max_length=50,
                        unique=True,
                    ),
                ),
                ("price", models.FloatField()),
                ("duration_months", models.IntegerField()),
                ("description", models.TextField()),
            ],
            options={
                "ordering": ["-created_at"],
                "abstract": False,
            },
            bases=(core.models.base_model.JSONSerializableMixin, models.Model),
        ),
        migrations.CreateModel(
            name="Subscription",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("start_date", models.DateField(auto_now_add=True)),
                ("end_date", models.DateField()),
                ("active", models.BooleanField(default=True)),
                (
                    "plan",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="payments.subscriptionplan",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscription",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "abstract": False,
            },
            bases=(core.models.base_model.JSONSerializableMixin, models.Model),
        ),
        migrations.CreateModel(
            name="PaymentMethod",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "method_type",
                    models.CharField(
                        choices=[("credit_card", "Credit Card"), ("paypal", "PayPal")],
                        max_length=50,
                    ),
                ),
                ("last_four_digits", models.CharField(max_length=4)),
                ("expiry_date", models.DateField()),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payment_methods",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("amount", models.FloatField()),
                ("currency", models.CharField(max_length=10)),
                (
                    "purpose",
                    models.CharField(
                        choices=[
                            ("Subscription", "Subscription"),
                            ("PrintOrder", "Print Order"),
                        ],
                        max_length=20,
                    ),
                ),
                ("transaction_id", models.CharField(max_length=100, unique=True)),
                ("status", models.CharField(default="Completed", max_length=20)),
                (
                    "billing_address",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="billing_payments",
                        to="payments.address",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "abstract": False,
            },
            bases=(core.models.base_model.JSONSerializableMixin, models.Model),
        ),
    ]
