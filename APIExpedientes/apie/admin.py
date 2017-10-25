# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from models import Expediente, Requisito, Observacion, Actualizacion, Usuario, Rol
# Register your models here.
admin.site.register(Expediente)
admin.site.register(Requisito)
admin.site.register(Observacion)
admin.site.register(Actualizacion)
admin.site.register(Usuario)
admin.site.register(Rol)
