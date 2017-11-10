# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User, AbstractUser

# Create your models here.
class Rol(models.Model):
    nombre = models.CharField(max_length=15)

    class Meta:
        verbose_name = 'rol'
        verbose_name_plural = 'roles'

    def __str__(self):
        return self.nombre

class Usuario(AbstractUser):
    codigo = models.CharField(max_length=6)
    rol = models.ForeignKey(Rol)

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
    fecha_recibido = models.DateTimeField()
    fecha_envio = models.DateTimeField()
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
