# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.
class Expediente(models.Model):
    tipo = models.CharField(max_length=1)
    fecha_entrada = models.DateField(name='Fecha de entrada')
    fecha_finalizacion = models.DateField(name='Fecha de finalizacion')
    remitente = models.CharField(max_length=100)
    numero_folios = models.CharField(max_length=10)
    completado = models.SmallIntegerField(default=0)

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
    usuario = models.IntegerField()

    class Meta:
        verbose_name = 'observacion'
        verbose_name_plural = 'observaciones'

class Actualizacion(models.Model):
    fecha_recibido = models.DateTimeField(name='Fecha de recibido')
    fecha_envido = models.DateTimeField(name='Fecha enviado')
    observaciones = models.TextField()
    expediente = models.ForeignKey(Expediente)
    usuario = models.IntegerField()
