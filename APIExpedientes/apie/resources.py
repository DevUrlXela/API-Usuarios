from django.db import IntegrityError
from django.contrib.auth import authenticate, login, logout
from django.conf.urls import url
from django.db.models import Q
from django.core import serializers

from tastypie.resources import ModelResource, Resource, ALL
from tastypie.serializers import Serializer
from tastypie.authorization import DjangoAuthorization, ReadOnlyAuthorization, Authorization
from tastypie.authentication import BasicAuthentication
from tastypie.exceptions import BadRequest
from tastypie.http import HttpUnauthorized, HttpForbidden, HttpCreated, HttpResponse
from tastypie.utils import trailing_slash
from tastypie.constants import ALL
from tastypie.api import Api
from tastypie import fields

from oauth2_provider.models import AccessToken, Application

from datetime import date, datetime, timedelta
import json

from models import Expediente, Requisito, Observacion, Actualizacion, Usuario, Rol, Estado
from authentication import (OAuth20Authentication, OAuth2ScopedAuthentication)
from tools import codigo, generar_clave

class RolResource(ModelResource):
    class Meta:
        queryset = Rol.objects.all()
        authorization = Authorization()
        authentication = OAuth20Authentication()
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
        self.user.email = bundle.data.get('email')
        self.user.save()

        self.token = generar_clave(self)

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
                '''
                token = generar_clave(self)
                application = Application.objects.get(user=user)

                options = {
                    'user': user,
                    'application': application,
                    'expires': datetime.now() + timedelta(minutes=30),
                    'token': token
                }

                access_token = AccessToken(**options)
                access_token.save()
                '''

                return self.create_response(request, {'success': True, 'user': user.id, 'rol':user.rol, 'token':token})
            else:
                return self.create_response(request, {'success': False, 'reason': 'baneado',}, HttpForbidden)
        else:
            return self.create_response(request, {'success': False, 'reason': 'incorrect', 'skip_login_redir':True}, HttpUnauthorized)

    def logout(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        access_token = AccessToken.objects.get(token=token)

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
            'tipo': ALL,
            'remitente': ALL,
            'firma': ALL,
            'usuario': ALL,
        }

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/noleidos%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('no_leidos'), name="expediente_noleidos"),
            url(r"^(?P<resource_name>%s)/crear%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('crear'), name="crear"),
            url(r"^(?P<resource_name>%s)/informacion/(?P<id>[\d]+)%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('informacion'), name="expediente_informacion"),
            url(r"^(?P<resource_name>%s)/finalizados%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('lista_finalizados'), name="expediente_finalizados"),
            url(r"^(?P<resource_name>%s)/trasferidos%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('lista_trasferidos'), name="expediente_trasferidos"),
            url(r'^(?P<resource_name>%s)/(?P<id>[\d]+)/leido%s$' %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('leido'), name='expediente_leido'),
            url(r'^(?P<resource_name>%s)/(?P<id>[\d]+)/autorizar%s$' %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('autorizado'), name='expediente_autorizado'),
        ]

    def crear(self, request, **kwargs):
        self.method_check(request, allowed=['post'])
        self.is_authenticated(request)
        #self.is_authorized(request)
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        tipo = data.get('tipo', '')
        fecha_entrada = date.today()
        remitente = data.get('remitente', '')
        folio = data.get('numero_folios', '')
        firma = data.get('firma', '')
        usuario = data.get('usuario', '')

        us = Usuario.objects.get(id=usuario)
        exp = Expediente(tipo=tipo, fecha_entrada=fecha_entrada, remitente=remitente, numero_folios=folio, firma=firma, usuario=us)
        exp.save()
        return self.create_response(request, {"success":True}, HttpCreated)

    def informacion(self, request, id, **kwargs):
        self.method_check(request, allowed=['get', 'post'])
        self.is_authenticated(request)
        #self.is_authorized(request)

        exp = Expediente.objects.get(id=id)
        return self.create_response(request, { "success":True, "tipo":exp.tipo, "fecha_entrada": exp.fecha_entrada, "fecha_finalizacion": exp.fecha_finalizacion,
                                               "remitente": exp.remitente, "numero_folios": exp.numero_folios, "completado": exp.completado, "leido": exp.leido,
                                               "firma": exp.firma, "aceptado": exp.aceptado, "usuario": exp.usuario.id})

    def lista_finalizados(self, request, **kwargs):
        self.method_check(request, allowed=['get', 'post'])
        self.is_authenticated(request)
        #self.is_authorized(request)
        data = serializers.serialize("json", Expediente.objects.filter(Q(usuario=request.user), Q(completado=1)))

        return HttpResponse(data, content_type='application/json', status=200)

    def lista_trasferidos(self,request, **kwargs):
        self.method_check(request, allowed=['get', 'post'])
        self.is_authenticated(request)
        #self.is_authorized(request)
        data = serializers.serialize("json", Actualizacion.objects.filter(usuario=request.user))

        return HttpResponse(data, content_type='application/json', status=200)

    def no_leidos(self, request, **kwargs):
        self.method_check(request, allowed=['get', 'post'])
        self.is_authenticated(request)
        #self.is_authorized(request)
        expediente = Expediente.objects.filter(Q(usuario=request.user), Q(leido=0)).count()

        return self.create_response(request, {'numero': expediente})

    def leido(self, request, id, **kwargs):
        self.method_check(request, allowed=['post', 'get'])
        self.is_authenticated(request)
        #self.is_authorized(request)
        #data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        #exp = data.get('id', '')
        expediente = Expediente.objects.get(id=id)
        expediente.leido = 1
        expediente.save()

        return self.create_response(request, { "success": True}, HttpCreated)

    def autorizado(self, request, id, **kwargs):
        self.method_check(request, allowed=['put', 'get'])
        self.is_authenticated(request)
        #self.is_authorized(request)
        #data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        #exp = data.get('id', '')
        expediente = Expediente.objects.get(id=id)
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
        filtering = {
            'id': ALL,
            'expediente': ALL,
        }
        resource_name = 'requisito'

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/expediente/(?P<id>[\d]+)/crear%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('crear'), name="requisto_crear"),
            url(r"^(?P<resource_name>%s)/expediente/(?P<id>[\d]+)/informacion%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('informacion'), name="requisito_informacion"),
            url(r"^(?P<resource_name>%s)/expediente/(?P<ide>[\d]+)/editar/(?P<idr>[\d]+)%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('editar'), name="requisto_editar"),
            url(r"^(?P<resource_name>%s)/finalizados%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('lista_finalizados'), name="requisito_cumplido"),
        ]

    def crear(self, request, id, **kwargs):
        self.method_check(request, allowed=['post'])
        self.is_authenticated(request)
        #self.is_authorized(request)
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        requisito = data.get('requisito', ' ')
        expediente = Expediente.objects.get(id=id)

        requisito = Requisito(requisito=requisito, expediente=expediente)
        requisito.save()

        return self.create_response(request, { "success": True}, HttpCreated)

    def informacion(self, request, id, **kwargs):
        self.method_check(request, allowed=['get', 'post'])
        self.is_authenticated(request)
        #self.is_authorized(request)

        expediente = Expediente.objects.filter(id=id)
        data = serializers.serialize("json", Requisito.objects.filter(expediente=expediente))

        return HttpResponse(data, content_type='application/json', status=200)

        #return self.create_response(request, {"success": True, "requisito": req.requisito, "cumplido":req.cumplido, "expediente": req.expediente.id })

    def editar(self, request, ide, idr, **kwargs):
        self.method_check(request, allowed=['put'])
        self.is_authenticated(request)
        #self.is_authorized(request)
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        req = Requisito.objects.get(id=idr)
        req.requisito = data.get('requisito', ' ')
        req.cumplido = data.get('cumplido', ' ')
        req.save()

        return self.create_response(request, { "success": True}, HttpCreated)

class ObservacionResource(ModelResource):
    expediente = fields.ForeignKey(ExpedienteResource, 'expediente')
    usuario = fields.ForeignKey(UsuarioResource, 'usuario')
    class Meta:
        queryset = Observacion.objects.all()
        authorization = Authorization()
        authentication = OAuth20Authentication()
        serializer = Serializer(formats=['json'])
        filtering = {
            'id': ALL,
            'expediente': ALL,
        }
        resource_name = 'observacion'

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/expediente/(?P<id>[\d]+)/crear%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('crear'), name="observacion_crear"),
            url(r"^(?P<resource_name>%s)/expediente/(?P<id>[\d]+)/informacion%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('informacion'), name="observacion_informacion"),
        ]

    def crear(self, request, id, **kwargs):
        self.method_check(request, allowed=['post'])
        self.is_authenticated(request)
        #self.is_authorized(request)
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        token = data.get('token', ' ')
        obs = data.get('observacion', ' ')
        at = AccessToken.objects.get(token=token)
        expediente = Expediente.objects.get(id=id)

        observacion = Observacion(observacion=obs, expediente=expediente, usuario=at.user)
        observacion.save()

        return self.create_response(request, { "success": True}, HttpCreated)

    def informacion(self, request, id, **kwargs):
        self.method_check(request, allowed=['post', 'get'])
        self.is_authenticated(request)
        #self.is_authorized(request)

        expediente = Expediente.objects.filter(id=id)
        data = serializers.serialize("json", Observacion.objects.filter(expediente=expediente))

        return HttpResponse(data, content_type='application/json', status=200)

class ActualizacionResource(ModelResource):
    expediente = fields.ForeignKey(ExpedienteResource, 'expediente')
    usuario = fields.ForeignKey(UsuarioResource, 'usuario')
    class Meta:
        queryset = Actualizacion.objects.all()
        authorization = Authorization()
        authentication = OAuth20Authentication()
        serializer = Serializer(formats=['json'])
        filtering = {
            'id': ALL,
            'expediente': ALL,
        }
        resource_name = 'actualizacion'

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/expediente/(?P<id>[\d]+)/crear%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('crear'), name="actualizacion_crear"),
            url(r"^(?P<resource_name>%s)/expediente/(?P<id>[\d]+)/transferencias%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('informacion'), name="actualizacion_informacion"),
            url(r"^(?P<resource_name>%s)/expediente/(?P<ide>[\d]+)/editar/(?P<ida>[\d]+)%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('editar'), name="actualizacion_editar"),
        ]

    def crear(self, request, id, **kwargs):
        self.method_check(request, allowed=['post'])
        self.is_authenticated(request)
        #self.is_authorized(request)
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        token = data.get('token', ' ')
        fecha_recibido = data.get('fecha_recibido', ' ')
        fecha_envio = data.get('fecha_envio', ' ')
        obs = data.get('observaciones', ' ')
        at = AccessToken.objects.get(token=token)
        expediente = Expediente.objects.get(id=id)

        observacion = Observacion(fecha_recibido=fecha_recibido, fecha_envio=fecha_envio, observaciones=obs, expediente=expediente, usuario=at.user)
        observacion.save()

        return self.create_response(request, { "success": True}, HttpCreated)

    def informacion(self, request, id, **kwargs):
        self.method_check(request, allowed=['get', 'post'])
        self.is_authenticated(request)
        #self.is_authorized(request)

        expediente = Expediente.objects.filter(id=id)
        data = serializers.serialize("json", Actualizacion.objects.filter(expediente=expediente).values())

        return HttpResponse(data, content_type='application/json', status=200)

        #return self.create_response(request, {"success": True, "requisito": req.requisito, "cumplido":req.cumplido, "expediente": req.expediente.id })

    def editar(self, request, ide, ida, **kwargs):
        self.method_check(request, allowed=['put'])
        self.is_authenticated(request)
        #self.is_authorized(request)
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        act = Actualizacion.objects.get(id=ida)
        act.fecha_recibido = data.get('fecha_recibido', ' ')
        act.fecha_envio = data.get('fecha_envio', ' ')
        act.observaciones = data.get('observaciones', ' ')
        act.save()

        return self.create_response(request, { "success": True}, HttpCreated)


class EstadoResource(ModelResource):
    expediente = fields.ForeignKey(ExpedienteResource, 'expediente')
    class Meta:
        queryset = Estado.objects.all()
        authorization = Authorization()
        authentication = OAuth20Authentication()
        serializer = Serializer(formats=['json'])
        filtering = {
            'id': ALL,
            'expediente': ALL,
        }
        resource_name = 'estado'

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/expediente/(?P<id>[\d]+)/crear%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('crear'), name="estado_crear"),
            url(r"^(?P<resource_name>%s)/expediente/(?P<id>[\d]+)/estados%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('informacion'), name="estado_informacion"),
        ]

    def crear(self, request, id, **kwargs):
        self.method_check(request, allowed=['post'])
        self.is_authenticated(request)
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        estado = data.get('estado', '')
        fecha = date.today()
        expediente = Expediente.objects.get(id=id)

        crear = Estado(estado=estado, fecha=fecha, expediente=expediente)
        crear.save()

        return self.create_response(request, {"success": True}, HttpCreated)

    def informacion(self, request, id, **kwargs):
        self.method_check(request, allowed=['post', 'get'])
        self.is_authenticated(request)
        #self.is_authorized(request)

        expediente = Expediente.objects.filter(id=id)
        data = serializers.serialize("json", Estado.objects.filter(expediente=expediente))

        return HttpResponse(data, content_type='application/json', status=200)
