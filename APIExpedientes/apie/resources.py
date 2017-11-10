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
from tastypie.paginator import Paginator
from tastypie import fields

from oauth2_provider.models import AccessToken, Application

from datetime import date, datetime, timedelta
import json
from django.core.serializers.json import DjangoJSONEncoder

from models import Expediente, Requisito, Observacion, Actualizacion, Usuario, Rol, Estado
from authentication import (OAuth20Authentication, OAuth2ScopedAuthentication)
from tools import codigo, generar_clave, DjangoOverRideJSONEncoder

class RolResource(ModelResource):
    class Meta:
        queryset = Rol.objects.all()
        authorization = Authorization()
        authentication = OAuth20Authentication()
        serializer = Serializer(formats=['json'])
        resource_name = 'rol'

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/usuarios%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('informacion'), name="rol_informacion"),
        ]

    def informacion(self, request, **kwargs):
        self.method_check(request, allowed=['post', 'get'])
        self.is_authenticated(request)
        #self.is_authorized(request)

        usuarios = Usuario.objects.all()
        values = []

        for u in usuarios:
            d = {'id': u.id, 'usuario': u.username, 'rol': u.rol.nombre}
            values.append(d)

        data = json.dumps(values)

        return HttpResponse(data, content_type='application/json', status=200)

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

                return self.create_response(request, {'success': True, 'user': user.id, 'username': user.username, 'rol':user.rol, 'token':token})
            else:
                return self.create_response(request, {'success': False, 'reason': 'baneado',}, HttpForbidden)
        else:
            return self.create_response(request, {'success': False, 'reason': 'incorrect', 'skip_login_redir':True}, HttpUnauthorized)

    def logout(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        #access_token = AccessToken.objects.get(token=token)

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
        limit = 1
        paginator_class = Paginator
        resource_name = 'expediente'
        filtering = {
            'id': ALL,
            'tipo': ALL,
            'remitente': ALL,
            'firma': ALL,
        }

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/noleidos%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('no_leidos'), name="expediente_noleidos"),
            url(r"^(?P<resource_name>%s)/inbox/(?P<pag>[\d]+)%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('inbox'), name="expediente_entrada"),
            url(r"^(?P<resource_name>%s)/crear%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('crear'), name="crear"),
            url(r"^(?P<resource_name>%s)/informacion/(?P<id>[\d]+)%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('informacion'), name="expediente_informacion"),
            url(r"^(?P<resource_name>%s)/finalizados/(?P<pag>[\d]+)%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('lista_finalizados'), name="expediente_finalizados"),
            url(r"^(?P<resource_name>%s)/trasferidos/(?P<pag>[\d]+)%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('lista_trasferidos'), name="expediente_trasferidos"),
            url(r'^(?P<resource_name>%s)/(?P<id>[\d]+)/leido%s$' %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('leido'), name='expediente_leido'),
            url(r'^(?P<resource_name>%s)/(?P<id>[\d]+)/autorizar%s$' %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('autorizar'), name='expediente_autorizar'),
            url(r'^(?P<resource_name>%s)/(?P<id>[\d]+)/aceptar%s$' %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('aceptar'), name='expediente_aceptar'),
            url(r"^(?P<resource_name>%s)/busqueda/(?P<id>[\d]+)%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('busqueda_rapida'), name="expediente_busqueda_rapida"),
        ]

    '''
    def get_list(self, request, **kwargs):
        base_bundle = self.build_bundle(request=request)
        objects = self.obj_get_list(bundle=base_bundle, **self.remove_api_resource_names(kwargs))
        sorted_objects = self.apply_sorting(objects, options=request.GET)

        if 'custom_uri' in kwargs:
            resource_uri = kwargs['custom_uri']
        else:
            resource_uri = self.get_resource_uri()

         paginator = self._meta.paginator_class(request.GET, sorted_objects, resource_uri=resource_uri, limit=self._meta.limit,
                                                max_limit=self._meta.max_limit, collection_name=self._meta.collection_name)
         to_be_serialized = paginator.page()

         bundles = []

         for obj in to_be_serialized[self._meta.collection_name]:
             bundle = self.build_bundle(obj=obj, request=request)
             bundles.append(self.full_dehydrate(bundle, for_list=True))

        to_be_serialized[self._meta.collection_name] = bundles
        to_be_serialized = self.alter_list_data_to_serialize(request, to_be_serialized)

        return self.create_response(request, to_be_serialized)
    '''

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

        exp = Expediente(tipo=tipo, fecha_entrada=fecha_entrada, remitente=remitente, numero_folios=folio, firma=firma)
        exp.save()

        est = Estado(estado="En espera", fecha= date.today(), expediente=exp)
        est.save()

        return self.create_response(request, {"success":True, "id": exp.id}, HttpCreated)

    def informacion(self, request, id, **kwargs):
        self.method_check(request, allowed=['get', 'post'])
        self.is_authenticated(request)
        #self.is_authorized(request)

        exp = Expediente.objects.get(id=id)
        return self.create_response(request, { "success":True, "tipo":exp.tipo, "fecha_entrada": exp.fecha_entrada, "fecha_finalizacion": exp.fecha_finalizacion,
                                               "remitente": exp.remitente, "numero_folios": exp.numero_folios, "completado": exp.completado, "leido": exp.leido,
                                               "firma": exp.firma, "aceptado": exp.aceptado})

    def inbox(self, request, pag, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)

        #data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        t = request.META['HTTP_AUTHORIZATION']
        t = t[7:]

        token = AccessToken.objects.get(token=t)
        user = Usuario.objects.get(id=token.user.id)
        obj = Actualizacion.objects.filter(recibido=user)

        response_data = []
        if obj.exists():
            for o in obj:
                d = {'id': o.expediente.id, 'enviado': o.enviado.username, 'observaciones': o.observaciones, 'fecha_envio': o.fecha_envio, 'leido': o.expediente.leido}
                response_data.append(d)

        limit = 2
        pag = int(pag)
        response_data = response_data[limit*(pag-1):limit*pag]
        #data = serializers.serialize("json", obj, fields=('expediente_id', 'enviado__username', 'observaciones', 'fecha_envio'))
        data = json.dumps(response_data, cls=DjangoOverRideJSONEncoder)

        return HttpResponse(data, content_type='application/json', status=200)

    def lista_finalizados(self, request, pag, **kwargs):
        self.method_check(request, allowed=['get', 'post'])
        self.is_authenticated(request)

        obj = Actualizacion.objects.filter(expediente__completado=1)

        response_data = []
        if obj.exists():
            for o in obj:
                data = {'id':x.expediente.id, 'tipo': x.expediente.tipo, 'fecha_entrada': x.expediente.fecha_entrada, 'fecha_finalizacion':x.expediente.fecha_finalizacion,
                        'remitente':x.expediente.remitente, 'folio': x.expediente.numero_folios}
                response_data.append(data)

        limit = 2
        pag = int(pag)
        response_data = response_data[limit*(pag-1):limit*pag]

        data = json.dumps(response_data, cls=DjangoJSONEncoder)

        return HttpResponse(data, content_type='application/json', status=200)

    def lista_trasferidos(self,request, pag, **kwargs):
        self.method_check(request, allowed=['get', 'post'])
        self.is_authenticated(request)
        #self.is_authorized(request)
        t = request.META['HTTP_AUTHORIZATION']
        t = t[7:]

        token = AccessToken.objects.get(token=t)
        user = Usuario.objects.get(id=token.user.id)
        obj = Actualizacion.objects.filter(enviado=user)

        response_data = []
        if obj.exists():
            for o in obj:
                d = {'id': o.expediente.id, 'enviado': o.enviado.username, 'observaciones': o.observaciones, 'fecha_envio': o.fecha_envio, 'leido': o.expediente.leido}
                response_data.append(d)

        limit = 2
        pag = int(pag)
        response_data = response_data[limit*(pag-1):limit*pag]
        #data = serializers.serialize("json", obj, fields=('expediente_id', 'enviado__username', 'observaciones', 'fecha_envio'))
        data = json.dumps(response_data, cls=DjangoOverRideJSONEncoder)

        return HttpResponse(data, content_type='application/json', status=200)

    def no_leidos(self, request, **kwargs):
        self.method_check(request, allowed=['get', 'post'])
        self.is_authenticated(request)
        #self.is_authorized(request)
        expediente = Actualizacion.objects.filter(Q(recibido=request.user), Q(expediente__leido=0)).count()

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

    def autorizar(self, request, id, **kwargs):
        self.method_check(request, allowed=['put', 'get'])
        self.is_authenticated(request)
        #self.is_authorized(request)
        #data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        #exp = data.get('id', '')
        expediente = Expediente.objects.get(id=id)
        expediente.completado = 1
        expediente.save()

        est = Estado(estado="Finalizado", fecha= date.today(), expediente = expediente)
        est.save()

        return self.create_response(request, {"success":True})

    def aceptar(self, request, id, **kwargs):
        self.method_check(request, allowed=['put', 'get'])
        self.is_authenticated(request)
        #self.is_authorized(request)
        #data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        #exp = data.get('id', '')
        expediente = Expediente.objects.get(id=id)
        expediente.aceptado = 1
        expediente.save()

        est = Estado(estado="En proceso", fecha= date.today(), expediente=expediente)
        est.save()

        return self.create_response(request, {"success":True}, HttpCreated)

    def busqueda_rapida(self, request, id, **kwargs):
        self.method_check(request, allowed=['get', 'post'])
        self.is_authenticated(request)

        exp = Expediente.objects.get(id=id)
        est = Estado.objects.get(expediente=exp)

        return self.create_response(request, { "estado": est.estado, "tipo": exp.tipo, "remitente": exp.remitente,
                                               "fecha_ingreso": exp.fecha_entrada, "firma": exp.firma})

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
    enviado = fields.ForeignKey(UsuarioResource, 'enviado')
    recibido = fields.ForeignKey(UsuarioResource, 'recibido')
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

        #token = data.get('token', ' ')
        fecha_recibido = data.get('fecha_recibido', ' ')
        fecha_envio = data.get('fecha_envio', ' ')
        obs = data.get('observaciones', ' ')
        ide = data.get('enviado', ' ')
        idr = data.get('recibido', ' ')
        print ide, idr, obs
        #at = AccessToken.objects.get(token=token)
        enviado = Usuario.objects.get(id=ide)
        recibido = Usuario.objects.get(id=idr)
        expediente = Expediente.objects.get(id=id)

        act = Actualizacion(fecha_recibido=fecha_recibido, fecha_envio=fecha_envio, observaciones=obs, expediente=expediente, enviado=enviado, recibido=recibido)
        act.save()

        return self.create_response(request, { "success": True}, HttpCreated)

    def informacion(self, request, id, **kwargs):
        self.method_check(request, allowed=['get', 'post'])
        self.is_authenticated(request)
        #self.is_authorized(request)

        expediente = Expediente.objects.filter(id=id)
        data = serializers.serialize("json", Actualizacion.objects.filter(expediente=expediente))

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
        act.recibido = data.get('recibido', ' ')
        act.save()

        return self.create_response(request, { "success": True})

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
