# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from models import Expediente, Requisito, Observacion, Actualizacion, Usuario, Rol, Estado
# Register your models here.
class UserCreationForm(forms.ModelForm):
    """Form para la creacion de usuarios"""
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'rol')

    def clean_password2(self):
        # Validacion de la contrasenia
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("No coincide")
        return password2

    def save(self, commit=True):
       # Guarda y hashea la contrasenia
       user = super(UserCreationForm, self).save(commit=False)
       user.set_password(self.cleaned_data["password1"])
       if commit:
           user.save()
       return user

class UserAdmin(BaseUserAdmin):
    form = UserCreationForm
    list_display = ('username', 'first_name', 'last_name', 'rol')
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'first_name', 'last_name', 'rol')}
        ),
    )
    search_fields = ('username', 'first_name', 'last_name', 'rol',)


admin.site.register(Expediente)
admin.site.register(Requisito)
admin.site.register(Observacion)
admin.site.register(Actualizacion)
admin.site.register(Usuario, UserAdmin)
admin.site.register(Rol)
admin.site.register(Estado)
