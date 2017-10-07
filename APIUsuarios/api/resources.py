from django.db import IntegrityError

from tastypie.resources import ModelResource, Resource
from tastypie.serializers import Serializer
from tastypie.authorization import DjangoAuthorization, ReadOnlyAuthorization, Authorization
from tastypie.authentication import BasicAuthentication
from tastypie.exceptions import BadRequest
from tastypie import fields
from datetime import date

from models import Grupo, Registro, Rol, Usuario

class GrupoResource(ModelResource):
    class Meta:
        queryset = Grupo.objects.all()
        authorization = Authorization()
        serializer = Serializer(formats=['json'])
        resource_name = 'grupo'

class RolResource(ModelResource):
    class Meta:
        queryset = Rol.objects.all()
        authorization = Authorization()
        serializer = Serializer(formats=['json'])
        resource_name = 'rol'

class UsuarioResource(ModelResource):
    class Meta:
        queryset = Usuario.objects.all()
        authorization = Authorization()
        serializer = Serializer(formats=['json'])
        resource_name = 'user'

class RegistroResource(ModelResource):
    class Meta:
        queryset = Registro.objects.all()
        authorization = Authorization()
        serializer = Serializer(formats=['json'])
        resource_name = 'reg'
