from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import Song, Profile

User = get_user_model()

class SongForm(forms.ModelForm):
    class Meta:
        model = Song
        fields = ['title', 'genre', 'price', 'path', 'cover']  # Добавлено 'cover'
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'genre': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'path': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'cover': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),  # Добавлен виджет для cover
        }

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Электронная почта')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Этот адрес электронной почты уже зарегистрирован.')
        return email

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['status', 'photo']
        widgets = {
            'status': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }