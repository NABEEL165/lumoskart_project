from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
# from .models import PRODUCT_MODEL



class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('customer', 'Customer'),
        ('influencer', 'Influencer'),
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)


class InfluencerProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='influencer_profile')
    photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    featured = models.BooleanField(default=False)  # Featured flag

    def __str__(self):
        return f"{self.user.username}'s Profile"


class InfluencerVideo(models.Model):
    influencer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='influencer_videos'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    video_file = models.FileField(upload_to='influencer_videos/')
    thumbnail = models.ImageField(upload_to='video_thumbnails/', blank=True, null=True)

    # Revert to string reference to avoid circular import issues
    products = models.ManyToManyField(
        'products.Product',
        blank=True,
        related_name='tagged_in_videos'
    )

    likes = models.PositiveIntegerField(default=0)
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Influencer Video'
        verbose_name_plural = 'Influencer Videos'

    def __str__(self):
        return f"{self.title} - {self.influencer.username}"




from django.db import models
from django.conf import settings

class OrderItem(models.Model):
    order = models.ForeignKey(
        "accounts.Order",      # referencing as a string fixes NameError
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="account_order_items"
    )

    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"

class WithdrawRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('completed', 'Completed'),
    ]
    influencer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='withdraw_requests'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField(blank=True, null=True)
    admin_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Withdraw Requests"

    def __str__(self):
        return f"Withdraw #{self.pk} - {self.influencer.username} (₹{self.amount})"


# accounts/models.py   (or wherever your Order model lives)

# accounts/models.py

from django.db import models
from django.conf import settings




class Order(models.Model):
    PENDING = 'Pending'
    COMPLETED = 'Completed'
    SHIPPED = 'Shipped'
    CANCELED = 'Canceled'

    ORDER_STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (COMPLETED, 'Completed'),
        (SHIPPED, 'Shipped'),
        (CANCELED, 'Canceled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    address = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    # THESE TWO FIELDS ARE REQUIRED FOR YOUR CURRENT DASHBOARD LOGIC
    commission_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.00
    )  # e.g. 10.00 = 10%

    commission_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )  # LumosKart's commission on this order

    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default=PENDING
    )

    def save(self, *args, **kwargs):
        # Auto-calculate commission_amount before saving
        if self.total_amount:
            self.commission_amount = self.total_amount * (self.commission_percentage / 100)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.id} - {self.user.email} - ₹{self.total_amount}"




from django.db import models
from accounts.models import CustomUser

class Video(models.Model):
    influencer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='videos')
    video_file = models.FileField(upload_to='reels/')
    caption = models.CharField(max_length=200, blank=True)
    is_approved = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reel by {self.influencer.username}"
