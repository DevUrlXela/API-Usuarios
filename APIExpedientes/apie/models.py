# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User, AbstractUser, UserManager

from datetime import date, datetime

# Create your models here.
class MyUserManager(UserManager):
    def create_user(self, username, first_name, last_name, rol, password=None):
        if not username:
            raise ValueError('Se necesita un nombre de usuario')

        user = self.model(
            username=username,
            first_name=first_name,
            last_name=last_name,
            rol=rol,
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

class Rol(models.Model):
    nombre = models.CharField(max_length=15)

    class Meta:
        verbose_name = 'rol'
        verbose_name_plural = 'roles'

    def __str__(self):
        return self.nombre

class Usuario(AbstractUser):
    codigo = models.CharField(max_length=6)
    first_name = models.CharField(max_length=35)
    last_name = models.CharField(max_length=35)
    rol = models.ForeignKey(Rol)

    objects = MyUserManager()

    #REQUIRED_FIELDS = ['first_name', 'last_name', 'username', 'rol']

    def __str__(self):
        return self.codigo

class Expediente(models.Model):
    tipo = models.CharField(max_length=20)
    fecha_entrada = models.DateField(auto_now=True)
    fecha_finalizacion = models.DateField(null=True)
    remitente = models.CharField(max_length=100)
    numero_folios = models.CharField(max_length=10)
    completado = models.SmallIntegerField(default=0)
    leido = models.SmallIntegerField(default=0)
    firma = models.CharField(max_length=15)
    aceptado = models.SmallIntegerField(default=0)
    #usuario = models.ForeignKey(Usuario)

    class Meta:
        verbose_name = 'expediente'
        verbose_name_plural = 'expedientes'

    def __unicode__(self):
        return self.tipo

    def __str__(self):
        return self.tipo

    def get(self, dato, **kwargs):
        options = {
            "remitente": self.remitente,
            "tipo": self.tipo,
            "fecha_entrada": self.fecha_entrada,
            "fecha_finalizacion": self.fecha_finalizacion,
            "completado": self.completado,
            "numero_folios": self.numero_folios,
        }

        return options.get(dato)

class Requisito(models.Model):
    requisito = models.CharField(max_length=100)
    cumplido = models.SmallIntegerField(default=0)
    expediente = models.ForeignKey(Expediente)

    class Meta:
        verbose_name = 'requisito'
        verbose_name_plural = 'requisitos'

    def __str__(self):
        return self.requisito

class Observacion(models.Model):
    observacion = models.TextField()
    expediente = models.ForeignKey(Expediente)
    usuario = models.ForeignKey(Usuario)

    class Meta:
        verbose_name = 'observacion'
        verbose_name_plural = 'observaciones'

class Actualizacion(models.Model):
    fecha_recibido = models.DateTimeField(null=True)
    fecha_envio = models.DateTimeField(auto_now=True)
    observaciones = models.TextField()
    expediente = models.ForeignKey(Expediente)
    enviado = models.ForeignKey(Usuario, null=True, related_name="enviado")
    recibido = models.ForeignKey(Usuario, null=True, related_name="recibido")

class Estado(models.Model):
    estado = models.CharField(max_length=10)
    fecha = models.DateField(auto_now=False)
    expediente = models.ForeignKey(Expediente)

    def __str__(self):
        return self.estado
