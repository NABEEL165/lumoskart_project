from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from .models import InfluencerProfile
from django.core.exceptions import ValidationError
import re
from .models import InfluencerVideo
from products.models import Product






class InfluencerRegisterForm(UserCreationForm):
    full_name = forms.CharField(max_length=255, required=True, label="Full Name")

    class Meta:
        model = CustomUser
        fields = ['full_name', 'username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'influencer'
        user.full_name = self.cleaned_data['full_name']
        if commit:
            user.save()
        return user

class CustomerRegisterForm(UserCreationForm):
    full_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={
        'placeholder': 'Your Name'
    }))
    phone = forms.CharField(max_length=15, required=True, widget=forms.TextInput(attrs={
        'placeholder': 'Phone Number'
    }))

    class Meta:
        model = CustomUser
        fields = ['username', 'full_name', 'email', 'phone', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'customer'
        user.full_name = self.cleaned_data['full_name']
        user.phone = self.cleaned_data['phone']
        if commit:
            user.save()
        return user



class InfluencerProfileForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True, label="Username")
    email = forms.EmailField(required=True, label="Email")
    full_name = forms.CharField(max_length=255, required=False, label="Full Name")
    phone = forms.CharField(max_length=15, required=False, label="Phone Number")

    class Meta:
        model = InfluencerProfile
        fields = ['photo', 'bio']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['username'].initial = user.username
            self.fields['email'].initial = user.email
            self.fields['full_name'].initial = user.full_name
            self.fields['phone'].initial = user.phone

        # Add Bootstrap classes for better UI
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    # ✅ Gmail validation using regex
    def clean_email(self):
        email = self.cleaned_data.get('email')
        gmail_pattern = r'^[a-zA-Z0-9._%+-]+@gmail\.com$'
        if not re.match(gmail_pattern, email):
            raise ValidationError("Please enter a valid Gmail address (must end with @gmail.com).")
        return email

    # ✅ Phone number validation (10 digits only)
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        phone_pattern = r'^[6-9]\d{9}$'  # Starts with 6–9, total 10 digits (Indian format)
        if phone and not re.match(phone_pattern, phone):
            raise ValidationError("Enter a valid 10-digit phone number starting with 6–9.")
        return phone

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']
        user.full_name = self.cleaned_data['full_name']
        user.phone = self.cleaned_data['phone']
        if commit:
            user.save()
            profile.save()
        return profile



# class VideoUploadForm(forms.ModelForm):
#     products = forms.ModelMultipleChoiceField(
#         queryset=Product.objects.none(),
#         widget=forms.CheckboxSelectMultiple,
#         required=False,
#         label="Tag Products"
#     )

#     class Meta:
#         model = InfluencerVideo
#         fields = ['title', 'description', 'video_file', 'thumbnail']
#         widgets = {
#             'title': forms.TextInput(attrs={'class': 'form-control'}),
#             'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
#             'video_file': forms.FileInput(attrs={'class': 'form-control-file'}),
#             'thumbnail': forms.FileInput(attrs={'class': 'form-control-file'}),
#         }

#     def __init__(self, *args, **kwargs):
#         self.influencer = kwargs.pop('influencer', None)
#         super().__init__(*args, **kwargs)
#         if self.influencer:
#             self.fields['products'].queryset = Product.objects.filter(influencer=self.influencer)


# # accounts/forms.py
# class VideoUploadForm(forms.ModelForm):
#     products = forms.ModelMultipleChoiceField(
#         queryset=Product.objects.none(),
#         widget=forms.CheckboxSelectMultiple,
#         required=False,
#         label="Tag Products in this Reel"
#     )

#     class Meta:
#         model = InfluencerVideo
#         fields = ['title', 'description', 'video_file', 'thumbnail', 'products']

#     def __init__(self, *args, **kwargs):
#         influencer = kwargs.pop('influencer', None)
#         super().__init__(*args, **kwargs)
#         if influencer:
#             self.fields['products'].queryset = Product.objects.filter(influencer=influencer)
#             self.instance.influencer = influencer

#     def save(self, commit=True):
#         video = super().save(commit=False)
#         video.influencer = self.influencer
#         if commit:
#             video.save()
#             # Save the many-to-many relationships
#             self.save_m2m()
#         return video


# accounts/forms.py
from django import forms
from .models import InfluencerVideo
from products.models import Product


class VideoUploadForm(forms.ModelForm):
    products = forms.ModelMultipleChoiceField(
        queryset=Product.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Tag Products in this Reel"
    )

    class Meta:
        model = InfluencerVideo
        fields = ['title', 'description', 'video_file', 'thumbnail', 'products']

    def __init__(self, *args, **kwargs):
        # Save influencer so we can use it in save() and clean()
        self.influencer = kwargs.pop('influencer', None)
        super().__init__(*args, **kwargs)

        if self.influencer:
            # Show only this influencer's products
            self.fields['products'].queryset = Product.objects.filter(influencer=self.influencer)
            # Auto-assign influencer to the video instance
            self.instance.influencer = self.influencer

    def clean_video_file(self):
        video = self.cleaned_data.get('video_file')
        if video:
            # Size limit: 100MB
            if video.size > 100 * 1024 * 1024:
                raise forms.ValidationError("Video file too large! Maximum 100MB allowed.")

            # File type check
            if not video.name.lower().endswith(('.mp4', '.mov', '.avi')):
                raise forms.ValidationError("Only MP4, MOV, or AVI files are allowed.")

        return video  # ← THIS WAS MISSING! (caused the syntax error)

    def save(self, commit=True):
        video = super().save(commit=False)
        if self.influencer:
            video.influencer = self.influencer
        if commit:
            video.save()
            self.save_m2m()  # saves the tagged products
        return video

    def save(self, commit=True):
        video = super().save(commit=False)
        # Use the influencer we saved in __init__
        if self.influencer:
            video.influencer = self.influencer

        if commit:
            video.save()
            # This saves the many-to-many products field
            self.save_m2m()

        return video


class VideoEditForm(forms.ModelForm):
    products = forms.ModelMultipleChoiceField(
        queryset=Product.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Tag Products"
    )

    class Meta:
        model = InfluencerVideo
        fields = ['title', 'description', 'thumbnail']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'thumbnail': forms.FileInput(attrs={'class': 'form-control-file'}),
        }

    def __init__(self, *args, **kwargs):
        self.influencer = kwargs.pop('influencer', None)
        super().__init__(*args, **kwargs)
        if self.influencer:
            self.fields['products'].queryset = Product.objects.filter(influencer=self.influencer)
            if self.instance.pk:
                self.fields['products'].initial = self.instance.products.all()

    # def save(self, commit=True):
    #     video = super().save(commit=False)
    #     if commit:
    #         video.save()
    #         # Update the many-to-many relationships
    #         video.products.set(self.cleaned_data['products'])
    #     return video

def save(self, commit=True):
    video = super().save(commit=False)
    if self.influencer:
        video.influencer = self.influencer
    if commit:
        video.save()
        self.save_m2m()  # This saves the tagged products
    return video

from django import forms
from .models import Video

