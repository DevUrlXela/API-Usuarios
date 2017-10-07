from django.db import IntegrityError
from django.contrib.auth import authenticate, login, logout
from django.conf.urls import url

from tastypie.resources import ModelResource, Resource
from tastypie.serializers import Serializer
from tastypie.authorization import DjangoAuthorization, ReadOnlyAuthorization, Authorization
from tastypie.authentication import BasicAuthentication
from tastypie.exceptions import BadRequest
from tastypie.http import HttpUnauthorized, HttpForbidden
from tastypie.utils import trailing_slash
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
    grupo = fields.ForeignKey(GrupoResource, 'grupo')
    class Meta:
        queryset = Rol.objects.all()
        authorization = Authorization()
        serializer = Serializer(formats=['json'])
        resource_name = 'rol'

class UsuarioResource(ModelResource):
    rol = fields.ForeignKey(GrupoResource, 'rol')
    class Meta:
        queryset = Usuario.objects.all()
        authorization = Authorization()
        serializer = Serializer(formats=['json'])
        resource_name = 'user'

    def obj_create(self, bundle, request=None, **kwargs):
        try:
            bundle = super(UsuarioResource, self).obj_create(bundle)
            bundle.obj.set_password(bundle.data.get('password'))
            bundle.obj.save()
        except IntegrityError:
            raise BadRequest('El usuario ya existe')

        return bundle

    def prepend_urls(self):
        return [
            url(r"^user/login/$", self.wrap_view('login'), name="api_login"),
            url(r"^user/logout/$", self.wrap_view('logout'), name='api_logout'),
        ]

    def login(self, request, **kwargs):
        self.method_check(request, allowed=['post'])
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        username = data.get('username', '')
        password = data.get('password', '')

        user = authenticate(username=username, password=password)

        if user:
            if user.is_active:
                login(request, user)
                return self.create_response(request, {'success': True, 'rol': user.rol})
            else:
                return self.create_response(request, {'success': False, 'reason': 'disabled',}, HttpForbidden)
        else:
            return self.create_response(request, {'success': False, 'reason': 'incorrect',}, HttpUnauthorized)

    def logout(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        if request.user and request.user.is_authenticated():
            logout(request)
            return self.create_response(request, {'success': True})
        else:
            return self.create_response(request, {'success': False}, HttpUnauthorized)

class RegistroResource(ModelResource):
    usuario = fields.ForeignKey(UsuarioResource, 'usuario')
    class Meta:
        queryset = Registro.objects.all()
        authorization = Authorization()
        serializer = Serializer(formats=['json'])
        resource_name = 'reg'
