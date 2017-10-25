from django.db import IntegrityError
from django.contrib.auth import authenticate, login, logout
from django.conf.urls import url
from django.db.models import Q

from tastypie.resources import ModelResource, Resource, ALL
from tastypie.serializers import Serializer
from tastypie.authorization import DjangoAuthorization, ReadOnlyAuthorization, Authorization
from tastypie.authentication import BasicAuthentication
from tastypie.exceptions import BadRequest
from tastypie.http import HttpUnauthorized, HttpForbidden, HttpCreated
from tastypie.utils import trailing_slash
from tastypie.constants import ALL
from tastypie.api import Api
from tastypie import fields

from oauth2_provider.models import AccessToken, Application

from datetime import date, datetime, timedelta

from models import Expediente, Requisito, Observacion, Actualizacion, Usuario, Rol, Estado
from authentication import (OAuth20Authentication, OAuth2ScopedAuthentication)

class RolResource(ModelResource):
    class Meta:
        queryset = Rol.objects.all()
        authorization = Authorization()
        #authentication = OAuth20Authentication()
        serializer = Serializer(formats=['json'])
        resource_name = 'rol'

class UsuarioResource(ModelResource):
    rol = fields.ForeignKey(RolResource, 'rol')
    class Meta:
        queryset = Usuario.objects.all()
        authorization = Authorization()
        #authentication = OAuth20Authentication()
        excludes = ['email', 'password', 'is_active', 'is_staff', 'is_superuser']
        filtering = {
            'username': ALL,
        }
        serializer = Serializer(formats=['json'])
        resource_name = 'user'

    def obj_create(self, bundle, request=None, **kwargs):
        bundle = super(UsuarioResource, self).obj_create(bundle)
        bundle.obj.set_password(bundle.data.get('password'))
        bundle.obj.save()
        self.user = Usuario.objects.get(codigo=bundle.data.get('codigo'))

        self.token = 'TOKEN' + self.user.__str__()

        ot_application = Application(
            user = self.user,
            redirect_uris = 'https://127.0.0.1:8000',
            client_type = Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
            name = 'app ' + self.user.__str__()
        )
        ot_application.save()

        options = {
            'user': self.user,
            'application': ot_application,
            'expires': datetime.now() + timedelta(days=10),
            'token': self.token
        }

        ot_access_token = AccessToken(**options)
        ot_access_token.save()

        return bundle

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/login%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('login'), name="api_login"),
            url(r'^(?P<resource_name>%s)/logout%s$' %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('logout'), name='api_logout'),
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
                token = AccessToken.objects.get(user=user)
                return self.create_response(request, {'success': True, 'user': user.id, 'rol':user.rol, 'token':token})
            else:
                return self.create_response(request, {'success': False, 'reason': 'baneado',}, HttpForbidden)
        else:
            return self.create_response(request, {'success': False, 'reason': 'incorrect', 'skip_login_redir':True}, HttpUnauthorized)

    def logout(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        if request.user and request.user.is_authenticated():
            logout(request)
            return self.create_response(request, {'success': True})
        else:
            return self.create_response(request, {'success': False}, HttpUnauthorized)

class ExpedienteResource(ModelResource):
    usuario = fields.ForeignKey(UsuarioResource, 'usuario')
    class Meta:
        queryset = Expediente.objects.all()
        authorization = Authorization()
        authentication = OAuth20Authentication()
        serializer = Serializer(formats=['json'])
        resource_name = 'expediente'
        filtering = {
            'id': ALL,
        }

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<token>[-\w]+)/noLeidos%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('noLeidos'), name="api_noLeidos"),
            url(r"^(?P<resource_name>%s)/(?P<token>[-\w]+)/crear%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('crear'), name="crear"),
            url(r'^(?P<resource_name>%s)/(?P<token>[-\w]+)/leido%s$' %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('leido'), name='api_leido'),
        ]

    def crear(self, request, **kwargs):
        self.method_check(request, allowed=['post'])
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        tipo = data.get('tipo', '')
        fecha_entrada = date.today()
        remitente = data.get('remitente', '')
        folio = data.get('folio', '')
        firma = data.get('firma', '')
        usuario = data.get('usuario', '')

        us = Usuario.objects.get(id=usuario)
        exp = Expediente(tipo=tipo, fecha_entrada=fecha_entrada, remitente=remitente, folio=folio, firma=firma, usuario=us)
        exp.save()
        return self.create_response(request, {"success":True}, HttpCreated)

    def noLeidos(self, request, token, **kwargs):
        self.method_check(request, allowed=['get'])
        expediente = Expediente.objects.filter(Q(usuario=request.user), Q(leido=0)).count()
        return self.create_response(request, {'numero': expediente})

    def leido(self, request, token, **kwargs):
        self.method_check(request, allowed=['put'])
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        exp = data.get('id', '')
        expediente = Expediente.objects.get(id=exp)
        expediente.leido = 1
        expediente.save()

        return self.create_response(request, {"success":True}, HttpCreated)

    def autorizado(self, request, token, **kwargs):
        self.method_check(request, allowed=['put'])
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        exp = data.get('id', '')
        expediente = Expediente.objects.get(id=exp)
        expediente.aceptado = 1
        expediente.save()



        return self.create_response(request, {"success":True}, HttpCreated)

class RequisitoResource(ModelResource):
    expediente = fields.ForeignKey(ExpedienteResource, 'expediente')
    class Meta:
        queryset = Requisito.objects.all()
        authorization = Authorization()
        authentication = OAuth20Authentication()
        serializer = Serializer(formats=['json'])
        resource_name = 'requisito'

class ObservacionResource(ModelResource):
    expediente = fields.ForeignKey(ExpedienteResource, 'expediente')
    class Meta:
        queryset = Observacion.objects.all()
        authorization = Authorization()
        authentication = OAuth20Authentication()
        serializer = Serializer(formats=['json'])
        resource_name = 'observacion'

class ActualizacionResource(ModelResource):
    expediente = fields.ForeignKey(ExpedienteResource, 'expediente')
    class Meta:
        queryset = Actualizacion.objects.all()
        authorization = Authorization()
        authentication = OAuth20Authentication()
        serializer = Serializer(formats=['json'])
        resource_name = 'actualizacion'

class EstadoResource(ModelResource):
    expediente = fields.ForeignKey(ExpedienteResource, 'expediente')
    class Meta:
        queryset = Estado.objects.all()
        authorization = Authorization()
        authentication = OAuth20Authentication()
        serializer = Serializer(formats=['json'])
        resource_name = 'estado'

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<token>[-\w]+)/crear%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('crear'), name="est_crear"),
            url(r"^(?P<resource_name>%s)/(?P<token>[-\w]+)/expediente/(?P<id>[\d]+)%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('estado_expediente'), name="estado_expediente"),
        ]

    def crear(self, request, **kwargs):
        self.method_check(request, allowed=['post'])
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        estado = data.get('estado', '')
        fecha = date.today()
        id_exp = data.get('expediente', '')
        expediente = Expediente.objects.get(id=id_exp)

        crear = Estado(estado=estado, fecha=fecha, expediente=expediente)
        crear.save()

        return self.create_response(request, {"success":True}, HttpCreated)

    def estado_expediente(self, request, id, **kwargs):
        self.method_check(request, allowed=['get'])
        estado = Estado.objects.get(id=id)

        return self.create_response(request, {"success":True, "estado":estado})
