# django_configs/forms.py
# Paste this file or add these classes inside your Django app's forms.py.

from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class LoginForm(forms.Form):
    """
    Bespoke Django Login Form using email as the identity parameter.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'you@example.com',
            'class': 'w-full pl-10 pr-4 py-2.5 bg-white border border-[#b5baff]/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#9fa1ff]/30 focus:border-[#9fa1ff] text-slate-900 transition-all font-semibold'
        })
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'class': 'w-full pl-10 pr-4 py-2.5 bg-white border border-[#b5baff]/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#9fa1ff]/30 focus:border-[#9fa1ff] text-slate-900 transition-all font-semibold'
        })
    )


class SignupForm(forms.Form):
    """
    Rigorous Django Signup Form with strict validation rules.
    """
    name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. Abid Ali',
            'class': 'w-full pl-10 pr-4 py-2.5 bg-white border border-[#b5baff]/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#9fa1ff]/30 focus:border-[#9fa1ff] text-slate-900 transition-all font-semibold'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'you@example.com',
            'class': 'w-full pl-10 pr-4 py-2.5 bg-white border border-[#b5baff]/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#9fa1ff]/30 focus:border-[#9fa1ff] text-slate-900 transition-all font-semibold'
        })
    )
    phone = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. +92 300 1234567',
            'class': 'w-full pl-10 pr-4 py-2.5 bg-white border border-[#b5baff]/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#9fa1ff]/30 focus:border-[#9fa1ff] text-slate-900 transition-all font-semibold'
        })
    )
    password = forms.CharField(
        min_length=8,
        required=True,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Min 8 characters',
            'class': 'w-full pl-10 pr-4 py-2.5 bg-white border border-[#b5baff]/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#9fa1ff]/30 focus:border-[#9fa1ff] text-slate-900 transition-all font-semibold'
        })
    )
    confirm_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Repeat your password',
            'class': 'w-full pl-10 pr-4 py-2.5 bg-white border border-[#b5baff]/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#9fa1ff]/30 focus:border-[#9fa1ff] text-slate-900 transition-all font-semibold'
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError("This email is already registered.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            phone = phone.strip()
            if User.objects.filter(phone=phone).exists():
                raise forms.ValidationError("This phone number is already registered.")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
            raise forms.ValidationError("Please ensure both passwords match.")
        
        return cleaned_data


class BecomeWorkerForm(forms.Form):
    """
    Onboarding Form for becoming a Workverse local freelance specialist
    """
    CATEGORY_CHOICES = [
        ('Plumber', 'Plumber Service'),
        ('Electrician', 'Electrician Service'),
        ('Painter', 'Painter Service'),
        ('Mechanic', 'Vehicle Mechanic'),
        ('Labour', 'General Helper'),
        ('Carpenter', 'Carpenter Work'),
        ('Other', 'Other (Specify in Bio)'),
    ]
    CITY_CHOICES = [
        ('Lahore', 'Lahore'),
        ('Karachi', 'Karachi'),
        ('Islamabad', 'Islamabad Capital'),
        ('Rawalpindi', 'Rawalpindi'),
        ('Other', 'Other (Specify in Bio)'),
    ]
    EXPERIENCE_CHOICES = [
        ('1 year', '1 Year Experience'),
        ('2 years', '2 Years Experience'),
        ('3 years', '3 Years Experience'),
        ('5 years', '5 Years Experience'),
        ('7 years', '7 Years Experience'),
        ('10 years', '10 Years Experience'),
        ('15+ years', '15+ Years Experience'),
    ]

    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full pl-10 pr-4 py-2 bg-white border border-[#b5baff]/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#9fa1ff]/30 focus:border-[#9fa1ff] text-slate-900 transition-all font-semibold'
        })
    )
    city = forms.ChoiceField(
        choices=CITY_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full pl-10 pr-4 py-2 bg-white border border-[#b5baff]/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#9fa1ff]/30 focus:border-[#9fa1ff] text-slate-900 transition-all font-semibold'
        })
    )
    experience = forms.ChoiceField(
        choices=EXPERIENCE_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full pl-10 pr-4 py-2 bg-white border border-[#b5baff]/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#9fa1ff]/30 focus:border-[#9fa1ff] text-slate-900 transition-all font-semibold'
        })
    )
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'placeholder': 'Describe your domestic technical services, tools, and specialties (optional)...',
            'rows': 3,
            'class': 'w-full pl-4 pr-4 py-2 bg-white border border-[#b5baff]/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#9fa1ff]/30 focus:border-[#9fa1ff] text-slate-900 transition-all font-semibold resize-none text-xs md:text-sm'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.apps import apps
        
        # Dynamically load categories from Category DB model
        try:
            Category = apps.get_model('myapp', 'Category')
            categories = [(cat.name, cat.name) for cat in Category.objects.all()]
        except Exception:
            categories = []
            
        if not categories:
            categories = [
                ('Plumber', 'Plumber'),
                ('Electrician', 'Electrician'),
                ('Painter', 'Painter'),
                ('Mechanic', 'Mechanic'),
                ('Labour', 'Labour'),
                ('Carpenter', 'Carpenter'),
                ('Other', 'Other'),
            ]
        self.fields['category'].choices = categories

        # Dynamically load cities from City DB model
        try:
            City = apps.get_model('myapp', 'City')
            cities = [(city.name, city.name) for city in City.objects.all()]
        except Exception:
            cities = []
            
        if not cities:
            cities = [
                ('Lahore', 'Lahore'),
                ('Karachi', 'Karachi'),
                ('Islamabad', 'Islamabad'),
                ('Rawalpindi', 'Rawalpindi'),
                ('Other', 'Other'),
            ]
        self.fields['city'].choices = cities

    def clean_bio(self):
        bio = self.cleaned_data.get('bio', '')
        return bio.strip() if bio else ''

