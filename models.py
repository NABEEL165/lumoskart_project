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

    # def save(self, *args, **kwargs):
    #     # Auto-calculate commission_amount before saving
    #     if self.total_amount:
    #         self.commission_amount = self.total_amount * (self.commission_percentage / 100)

def save(self, *args, **kwargs):
        # Auto-calculate commission_amount before saving
        if self.total_amount:
            try:
                commission_percentage = self.commission_percentage
            except AttributeError:
                commission_percentage = 20.0  # Default to 20% if field doesn't exist
            self.commission_amount = self.total_amount * (commission_percentage / Decimal('100'))



            # Check if status is being updated to Shipped or Completed
        old_instance = None
        if self.pk:  # If this is an update (not a new instance)
            try:
                old_instance = Order.objects.get(pk=self.pk)
            except Order.DoesNotExist:
                pass


        super().save(*args, **kwargs)

 # Auto-update influencer earnings after delivery
        if old_instance and self.status in [self.SHIPPED, self.COMPLETED] and \
           old_instance.status not in [self.SHIPPED, self.COMPLETED]:
            # Calculate and update influencer earnings
            for item in self.items.all():
                if item.product and item.product.influencer:
                    # In a real implementation, you might want to track influencer earnings
                    # in a separate model or field. For now, we just log the action.
                    pass

def __str__(self):
    return f"Order #{self.id} - {self.user.email} - ₹{self.total_amount}"
    def get_status_display_choices(self):
        return self.ORDER_STATUS_CHOICES


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


class InfluencerApplication(models.Model):
    CATEGORY_CHOICES = [
        ('fashion', 'Fashion'),
        ('tech', 'Tech'),
        ('gaming', 'Gaming'),
        ('art', 'Art'),
        ('food', 'Food & Cooking'),
        ('fitness', 'Fitness'),
        ('travel', 'Travel'),
        ('beauty', 'Beauty'),
        ('education', 'Education'),
        ('lifestyle', 'Lifestyle'),
        ('music', 'Music'),
        ('sports', 'Sports'),
        ('other', 'Other'),
    ]

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='influencer_application')
    instagram_handle = models.CharField(max_length=100, blank=True, null=True, help_text="Instagram username (without @)")
    youtube_channel = models.CharField(max_length=200, blank=True, null=True, help_text="YouTube channel URL")
    tiktok_handle = models.CharField(max_length=100, blank=True, null=True, help_text="TikTok username (without @)")
    other_social = models.CharField(max_length=200, blank=True, null=True, help_text="Other social media handles")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    portfolio_links = models.TextField(blank=True, null=True, help_text="Links to portfolio, previous work, etc. (one per line)")
    video_upload = models.FileField(upload_to='influencer_applications/', blank=True, null=True, help_text="Upload a sample video")
    bio = models.TextField(max_length=500, blank=True, null=True, help_text="Tell us about yourself and your content")
    followers_count = models.PositiveIntegerField(default=0, help_text="Approximate number of followers")

    # Admin approval fields
    is_approved = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True, null=True)
    reviewed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_applications')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Influencer Application ({'Approved' if self.is_approved else 'Pending'})"











        # Model to track which users liked which videos
class VideoLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='video_likes'
    )
    video = models.ForeignKey(
        InfluencerVideo,
        on_delete=models.CASCADE,
        related_name='user_likes'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'video')  # Prevent duplicate likes

    def __str__(self):
        return f"{self.user.username} liked {self.video.title}"












class Banner(models.Model):
    SECTION_CHOICES = (
        ('hero', 'Hero Slider'),
        ('middle', 'Middle Section'),
        ('bottom', 'Bottom Section'),
    )
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='banners/')
    link_url = models.URLField(blank=True, help_text="Target URL when banner is clicked")
    section = models.CharField(max_length=20, choices=SECTION_CHOICES, default='hero')
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['section', 'order']
        verbose_name = 'Banner & Slider'
        verbose_name_plural = 'Banners & Sliders'

    def __str__(self):
        return f"{self.title} ({self.get_section_display()})"


class PageContent(models.Model):
    slug = models.SlugField(unique=True, help_text="e.g. 'about-us', 'terms', 'help'")
    title = models.CharField(max_length=200)
    content = models.TextField(help_text="HTML/Content for the page")
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    thumbnail = models.ImageField(upload_to='blog/', blank=True, null=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class PromoVideo(models.Model):
    title = models.CharField(max_length=200)
    video_file = models.FileField(upload_to='promo_videos/')
    thumbnail = models.ImageField(upload_to='promo_thumbnails/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


