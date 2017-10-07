# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser

# Create your models here.
class Grupo(models.Model):
    grupo = models.CharField(max_length=45)

    class Meta:
        verbose_name = 'grupo'
        verbose_name_plural = 'grupos'

    def __str__(self):
        return self.grupo

class Rol(models.Model):
    permiso = models.SmallIntegerField(default=0)
    grupo = models.ForeignKey(Grupo)

    class Meta:
        verbose_name = 'rol'
        verbose_name_plural = 'roles'

class Usuario(AbstractUser):
    rol = models.ForeignKey(Grupo)

class Registro(models.Model):
    entrada = models.DateTimeField()
    salida = models.DateTimeField()
    app = models.IntegerField()
    usuario = models.ForeignKey(Usuario)

    class Meta:
        verbose_name = 'registro'
        verbose_name_plural = 'registros'
        ordering = ['entrada']
