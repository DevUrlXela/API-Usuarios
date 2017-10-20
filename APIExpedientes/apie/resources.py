from django.db import IntegrityError
from django.contrib.auth import authenticate, login, logout
from django.conf.urls import url

from tastypie.resources import ModelResource, Resource, ALL
from tastypie.serializers import Serializer
from tastypie.authorization import DjangoAuthorization, ReadOnlyAuthorization, Authorization
from tastypie.authentication import BasicAuthentication, ApiKeyAuthentication
from tastypie.exceptions import BadRequest
from tastypie.http import HttpUnauthorized, HttpForbidden
from tastypie.utils import trailing_slash
from tastypie import fields
from datetime import date

from models import Expediente, Requisito, Observacion, Actualizacion

class ExpedienteResource(ModelResource):
    class Meta:
        queryset = Expediente.objects.all()
        authorization = Authorization()
        serializer = Serializer(formats=['json'])
        resource_name = 'expediente'
        filtering = {
            'id': ALL,
        }

class RequisitoResource(ModelResource):
    expediente = fields.ForeignKey(ExpedienteResource, 'expediente')
    class Meta:
        queryset = Requisito.objects.all()
        authorization = Authorization()
        serializer = Serializer(formats=['json'])
        resource_name = 'requisito'

class ObservacionResource(ModelResource):
    expediente = fields.ForeignKey(ExpedienteResource, 'expediente')
    class Meta:
        queryset = Observacion.objects.all()
        authorization = Authorization()
        serializer = Serializer(formats=['json'])
        resource_name = 'Observacion'

class ActualizacionResource(ModelResource):
    expediente = fields.ForeignKey(ExpedienteResource, 'expediente')
    class Meta:
        queryset = Actualizacion.objects.all()
        authorization = Authorization()
        serializer = Serializer(formats=['json'])
        resource_name = 'Actualizacion'
