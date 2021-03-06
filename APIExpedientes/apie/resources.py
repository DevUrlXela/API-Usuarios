from django.db import IntegrityError
from django.contrib.auth import authenticate, login, logout
from django.conf.urls import url
from django.db.models import Q #, Subquery, OuterRef
from django.core import serializers
from django.utils import timezone

from tastypie.resources import ModelResource, Resource, ALL
from tastypie.serializers import Serializer
from tastypie.authorization import DjangoAuthorization, ReadOnlyAuthorization, Authorization
from tastypie.authentication import BasicAuthentication
from tastypie.exceptions import BadRequest
from tastypie.http import HttpUnauthorized, HttpForbidden, HttpCreated, HttpResponse, HttpAccepted
from tastypie.utils import trailing_slash
from tastypie.constants import ALL
from tastypie.api import Api
from tastypie.paginator import Paginator
from tastypie import fields

from oauth2_provider.models import AccessToken, Application

from datetime import date, datetime, timedelta
from django.core.serializers.json import DjangoJSONEncoder

from models import Expediente, Requisito, Observacion, Actualizacion, Usuario, Rol, Estado
from authentication import (OAuth20Authentication, OAuth2ScopedAuthentication)
from tools import codigo, generar_clave, DjangoOverRideJSONEncoder, validarFecha

import json
import xlwt, os, time

from reportlab.platypus import (SimpleDocTemplate, PageBreak, Image, Spacer,
Paragraph, Table, TableStyle)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from django.conf import settings

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
        #bundle.obj.set_username(bundle.data.get('username'))
        bundle.obj.set_password(bundle.data.get('password'))
        #bundle.obj.set_rol(bundle.data.get('rol'))
        bundle.obj.save()

        self.user = Usuario.objects.get(username=bundle.data.get('username'))
        self.user.username = bundle.data.get('username')
        self.user.rol = bundle.data.get('rol')
        self.user.is_staff = 1
        self.user.is_admin = 1
        self.user.save()
        '''
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


        url = 'http://192.168.1.5:8000/usuarios/user/'

        headers = {'Content-Type': 'application/json'}
        data_string = json.dumps({"password":bundle.data.get('password'),"username":bundle.data.get('username'),"is_active":bundle.data.get('is_active'),"codigo":str(self.user)})
        contenido = requests.post(url,data_string,headers=headers)
        print(data_string)
        if contenido.status_code == 201:
            print(str(contenido.status_code))
        else:
            print("Error: "+str(contenido.status_code))
        '''

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

                try:
                    application = Application.objects.get(user=user)
                except Application.DoesNotExist:
                    application = None

                if application != None:
                    token = generar_clave(self)
                    t = AccessToken.objects.get(user=user)
                    t.token = token
                    t.expires = datetime.now() + timedelta(days=1)
                    t.save()

                    return self.create_response(request, {'success': True, 'user': user.id, 'username': user.username, 'rol':user.rol, 'token':token})
                else:
                    ot_application = Application(
                        user = user,
                        redirect_uris = 'https://127.0.0.1:8000',
                        client_type = Application.CLIENT_CONFIDENTIAL,
                        authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
                        name = 'application'
                    )
                    ot_application.save()

                    token = generar_clave(self)
                    options = {
                        'user': user,
                        'application': ot_application,
                        'expires': datetime.now() + timedelta(days=1),
                        'token': token
                    }

                    ot_access_token = AccessToken(**options)
                    ot_access_token.save()

                    return self.create_response(request, {'success': True, 'user': user.id, 'username': user.username, 'rol':user.rol, 'token':token})
            else:
                return self.create_response(request, {'success': False, 'reason': 'Suspendido',}, HttpForbidden)
        else:
            return self.create_response(request, {'success': False, 'reason': 'incorrect', 'skip_login_redir':True}, HttpUnauthorized)

    def logout(self, request, **kwargs):
        self.method_check(request, allowed=['get'])

        if request.user and request.user.is_authenticated():
            token = AccessToken.objects.get(user=request.user)
            token.expires = datetime.now() + timedelta(hours=1)
            logout(request)
            return self.create_response(request, {'success': True, 'mensaje': 'adios ' + request.user.username})
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
            url(r"^(?P<resource_name>%s)/(?P<id>[\d]+)/editar%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('editar'), name="expediente_editar"),
            url(r"^(?P<resource_name>%s)/informacion/(?P<id>[\d]+)%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('informacion'), name="expediente_informacion"),
            url(r"^(?P<resource_name>%s)/finalizados/(?P<pag>[\d]+)%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('lista_finalizados'), name="expediente_finalizados"),
            url(r"^(?P<resource_name>%s)/transferidos/(?P<pag>[\d]+)%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('lista_transferidos'), name="expediente_trasferidos"),
            url(r'^(?P<resource_name>%s)/(?P<id>[\d]+)/leido%s$' %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('leido'), name='expediente_leido'),
            url(r'^(?P<resource_name>%s)/(?P<id>[\d]+)/autorizar%s$' %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('autorizar'), name='expediente_autorizar'),
            url(r'^(?P<resource_name>%s)/(?P<id>[\d]+)/aceptar%s$' %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('aceptar'), name='expediente_aceptar'),
            url(r"^(?P<resource_name>%s)/busquedarapida/(?P<id>[\d]+)%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('busqueda_rapida'), name="expediente_busqueda_rapida"),
            url(r"^(?P<resource_name>%s)/permiso/(?P<id>[\d]+)%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('permiso'), name="expediente_permiso"),
            url(r'^(?P<resource_name>%s)/(?P<id>[\d]+)/confirmar%s$' %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('confirmar'), name="expediente_confirmar"),
            url(r'^(?P<resource_name>%s)/busqueda/(?P<pag>[\d]+)%s$' %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('busqueda'), name="expediente_busqueda"),
            url(r"^(?P<resource_name>%s)/reporte%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('reporte'), name="expediente_reporte"),
            url(r"^(?P<resource_name>%s)/reporte_pdf%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('reporte_pdf'), name="expediente_reporte_pdf"),
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

        recibido = Usuario.objects.get(id=1)
        t = request.META['HTTP_AUTHORIZATION']
        t = t[7:]

        token = AccessToken.objects.get(token=t)
        enviado = Usuario.objects.get(id=token.user.id)

        act = Actualizacion(observaciones="Nuevo expediente", enviado=enviado, recibido=recibido, expediente=exp)
        act.save()

        return self.create_response(request, {"success":True, "id": exp.id}, HttpCreated)

    def editar(self, request, id, **kwargs):
        self.method_check(request, allowed=['put'])
        self.is_authenticated(request)

        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        tipo = data.get('tipo', ' ')
        remitente = data.get('remitente', ' ')
        folio = data.get('folio', ' ')
        firma = data.get('firma', ' ')

        exp = Expediente.objects.get(id=id)

        exp.tipo = tipo
        exp.remitente = remitente
        exp.folio = folio
        exp.firma = firma

        exp.save()

        return self.create_response(request, {"success":True, "id": exp.id}, HttpCreated)

    def informacion(self, request, id, **kwargs):
        self.method_check(request, allowed=['get', 'post'])
        self.is_authenticated(request)

        exp = Expediente.objects.get(id=id)
        return self.create_response(request, { "success":True, "id":exp.id ,"tipo":exp.tipo, "fecha_entrada": exp.fecha_entrada, "fecha_finalizacion": exp.fecha_finalizacion,
                                               "remitente": exp.remitente, "numero_folios": exp.numero_folios, "completado": exp.completado, "leido": exp.leido,
                                               "firma": exp.firma, "aceptado": exp.aceptado})

    def inbox(self, request, pag, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)

        t = request.META['HTTP_AUTHORIZATION']
        t = t[7:]

        token = AccessToken.objects.get(token=t)
        user = Usuario.objects.get(id=token.user.id)
        #q1 = Actualizacion.objects.all().distinct()[:1]
        #obj = Actualizacion.objects.filter(Q(recibido=user), ~Q(enviado=user) | Q(fecha_recibido=None)).order_by('-fecha_envio')
        obj = Actualizacion.objects.all()

        ids = []
        res = []
        for o in obj:
            ids.append(o.expediente.id)
            res.append(o.id)
            if o.expediente.id in ids:
                res[ids.index(o.expediente.id)] = o.id
            else:
                res.append(o.id)

        obj = Actualizacion.objects.filter(Q(recibido=user), ~Q(enviado=user) | Q(fecha_recibido=None), Q(id__in=res)).order_by('-fecha_envio')

        limit = 10
        pags = len(obj)
        total = 0

        while pags > 0:
            pags = pags - limit
            total = total + 1

        dd = {}
        dd['meta'] = {}
        dd['meta']['limit'] = 10
        dd['meta']['total'] = total

        dd['objects'] = []
        if obj.exists():
            for o in obj:
                d = {'id': o.expediente.id, 'enviado': o.enviado.username, 'observaciones': o.observaciones, 'fecha_envio': o.fecha_envio, 'leido': o.expediente.leido}
                dd['objects'].append(d)

        pag = int(pag)
        dd['objects'] = dd['objects'][limit*(pag-1):limit*pag]

        data = json.dumps(dd, cls=DjangoOverRideJSONEncoder)

        return HttpResponse(data, content_type='application/json', status=200)

    def lista_finalizados(self, request, pag, **kwargs):
        self.method_check(request, allowed=['get', 'post'])
        self.is_authenticated(request)

        t = request.META['HTTP_AUTHORIZATION']
        t = t[7:]

        token = AccessToken.objects.get(token=t)
        user = Usuario.objects.get(id=token.user.id)

        if user.rol.nombre == "Director":
            obj = Actualizacion.objects.all()

            ids = []
            res = []
            for o in obj:
                ids.append(o.expediente.id)
                res.append(o.id)
                if o.expediente.id in ids:
                    res[ids.index(o.expediente.id)] = o.id
                else:
                    res.append(o.id)

            obj = Actualizacion.objects.filter(Q(expediente__completado=1), Q(id__in=res))

            limit = 2
            pags = len(obj)
            total = 0

            while pags > 0:
                pags = pags - limit
                total = total + 1

            dd = {}
            dd['meta'] = {}
            dd['meta']['limit'] = 2
            dd['meta']['total'] = total

            dd['objects'] = []
            if obj.exists():
                for o in obj:
                    print o.expediente.id
                    d = {'id': o.expediente.id, 'enviado': o.enviado.username, 'observaciones': o.observaciones, 'fecha_envio': o.fecha_envio, 'leido': o.expediente.leido}
                    dd['objects'].append(d)

            pag = int(pag)
            dd['objects'] = dd['objects'][limit*(pag-1):limit*pag]

            data = json.dumps(dd, cls=DjangoJSONEncoder)

            return HttpResponse(data, content_type='application/json', status=200)

        return self.create_response(request, {'success': False}, HttpUnauthorized)

    def lista_transferidos(self,request, pag, **kwargs):
        self.method_check(request, allowed=['get', 'post'])
        self.is_authenticated(request)

        t = request.META['HTTP_AUTHORIZATION']
        t = t[7:]

        token = AccessToken.objects.get(token=t)
        user = Usuario.objects.get(id=token.user.id)
        obj = Actualizacion.objects.filter(Q(enviado=user), Q(fecha_recibido=None))

        limit = 2
        pags = len(obj)
        total = 0

        while pags > 0:
            pags = pags - limit
            total = total + 1

        dd = {}
        dd['meta'] = {}
        dd['meta']['limit'] = 2
        dd['meta']['total'] = total

        dd['objects'] = []
        if obj.exists():
            for o in obj:
                d = {'id': o.expediente.id, 'enviado': o.recibido.username, 'observaciones': o.observaciones, 'fecha_envio': o.fecha_envio, 'leido': o.expediente.leido}
                dd['objects'].append(d)

        pag = int(pag)
        dd['objects'] = dd['objects'][limit*(pag-1):limit*pag]

        data = json.dumps(dd, cls=DjangoOverRideJSONEncoder)

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
        expediente.fecha_finalizacion = date.today()
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

        act = Actualizacion.objects.filter(expediente=expediente)
        act[len(act)-1].fecha_recibido = datetime.now()
        act[len(act)-1].save()

        return self.create_response(request, {"success":True}, HttpCreated)

    def busqueda_rapida(self, request, id, **kwargs):
        self.method_check(request, allowed=['get', 'post'])
        self.is_authenticated(request)

        exp = Expediente.objects.get(id=id)
        est = Estado.objects.filter(expediente=exp)

        return self.create_response(request, { "estado": est[len(est)-1].estado, "tipo": exp.tipo, "remitente": exp.remitente,
                                               "fecha_ingreso": exp.fecha_entrada, "firma": exp.firma})

    def busqueda(self, request, pag, **kwargs):
        self.method_check(request, allowed=['post'])
        self.is_authenticated(request)

        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        bus = data.get('busqueda', ' ')

        if validarFecha(bus):
            obj = Expediente.objects.filter(Q(fecha_entrada=bus) | Q(fecha_finalizacion=bus))
        else:
            obj = Expediente.objects.filter(Q(tipo__exact=bus) | Q(remitente__exact=bus) | Q(numero_folios__exact=bus) | Q(
                                            firma__exact=bus))

        limit = 2
        pags = len(obj)
        total = 0

        while pags > 0:
            pags = pags - limit
            total = total + 1

        dd = {}
        dd['meta'] = {}
        dd['meta']['limit'] = 2
        dd['meta']['total'] = total

        dd['objects'] = []

        if obj.exists():
            for o in obj:
                d = {"id":o.id, "tipo": o.tipo, "remitente": o.remitente, "fecha_ingreso": o.fecha_entrada, "firma": o.firma}
                dd['objects'].append(d)

        pag = int(pag)
        dd['objects'] = dd['objects'][limit*(pag-1):limit*pag]

        data = json.dumps(dd, cls=DjangoJSONEncoder)

        return HttpResponse(data, content_type='application/json', status=200)

    def permiso(self, request, id, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)

        t = request.META['HTTP_AUTHORIZATION']
        t = t[7:]

        token = AccessToken.objects.get(token=t)
        user = Usuario.objects.get(id=token.user.id)
        exp = Expediente.objects.get(id=id)
        act = Actualizacion.objects.filter(Q(recibido=user), Q(expediente=exp))

        autorizar = 0
        aceptar = 0
        confirmar = 0
        modificar = 0
        transferir = 0

        if user.rol.nombre == "Director" and exp.completado != 1:
            autorizar = 1

        if act.exists():
            modificar = 1
            transferir = 1

        if exp.aceptado != 1 and user.rol.nombre == "Director":
            aceptar = 1

        print len(act)
        if act.exists():
            if act[len(act)-1].fecha_recibido != None:
                confirmar = 1

        return self.create_response(request, {'autorizar': autorizar, 'aceptar':aceptar, 'confirmar_recibido': confirmar, 'modificar': modificar, 'transferir': transferir}, HttpAccepted)

    def confirmar(self, request, id, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)

        exp = Expediente.objects.get(id=id)
        act = Actualizacion.objects.filter(expediente=exp)

        act[len(act)-1].fecha_recibido = datetime.now()
        act[len(act)-1].save()

        return self.create_response(request, { "success": True})

    def reporte(self, request, **kwargs):
        from django.conf import settings
        self.method_check(request, allowed=['post'])
        self.is_authenticated(request)

        t = request.META['HTTP_AUTHORIZATION']
        t = t[7:]

        token = AccessToken.objects.get(token=t)
        user = Usuario.objects.get(id=token.user.id)

        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename=expedientes.xls'

        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        remitente = data.get('remitente')
        fecha_entrada = data.get('fecha_entrada')
        numero_folios = data.get('numero_folios')
        tipo = data.get('tipo')
        completado = data.get('completado')
        fecha_finalizacion = data.get('fecha_finalizacion')
        estado = data.get('estado')
        comple = 0
        if completado == True:
            comple = 1
        else:
            comple = 0


        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Reporte')

        row_num = 0
        font_style = xlwt.XFStyle()
        font_style.font.bold = True

        titulos = ['Remitente', 'Tipo', 'Fecha de entrada', 'Fecha de finalizacion', 'Completado', 'Folio']
        campos = ['remitente', 'tipo', 'fecha_entrada', 'fecha_finalizacion', 'completado', 'numero_folios']
        opciones = [remitente, tipo, fecha_entrada, fecha_finalizacion, completado, numero_folios]
        cols = []
        fields = []

        for i, op in enumerate(opciones):
            if op == 1:
                cols.append(titulos[i])
                fields.append(campos[i])

        for col in range(len(cols)):
            ws.write(row_num, col, cols[col], font_style)
            ws.col(col).width = 7000

        font_style = xlwt.XFStyle()

        rows = rows = Expediente.objects.filter(Q(completado=comple), Q(fecha_entrada__range=(fecha_inicio,fecha_fin)))
        if estado == 0:
            rows = Expediente.objects.filter(Q(completado=comple), Q(fecha_entrada__range=(fecha_inicio,fecha_fin)))
        elif estado == 1:
            rows = Expediente.objects.filter(Q(completado=comple), Q(fecha_entrada__range=(fecha_inicio,fecha_fin)),Q(estado__estado = str(estado)))
        elif estado == 2:
            rows = Expediente.objects.filter(Q(completado=comple), Q(fecha_entrada__range=(fecha_inicio,fecha_fin)),Q(estado__estado = str(estado)))
        elif estado == 3:
            rows = Expediente.objects.filter(Q(completado=comple), Q(fecha_entrada__range=(fecha_inicio,fecha_fin)),Q(estado__estado = str(estado)))

        rows.values_list(*fields)
        for row in rows:
            row_num += 1
            for col_num, elem in enumerate(fields):
                ws.write(row_num, col_num, row.get(elem), font_style)

        fecha = datetime.now()
        nombre = "reporte" + str(fecha.year) + str(fecha.month) + str(fecha.day) + str(fecha.hour) + str(fecha.minute) + str(fecha.second) + ".xls"
        print nombre
        path = settings.MEDIA_ROOT + nombre
        wb.save(path)
        url = settings.MEDIA_URL + nombre
        return self.create_response(request, {'url': url}, status=200)

    def reporte_pdf(self, request, **kwargs):
        self.method_check(request, allowed=['post'])
        self.is_authenticated(request)

        t = request.META['HTTP_AUTHORIZATION']
        t = t[7:]

        token = AccessToken.objects.get(token=t)
        user = Usuario.objects.get(id=token.user.id)

        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        remitente = data.get('remitente')
        fecha_entrada = data.get('fecha_entrada')
        numero_folios = data.get('numero_folios')
        tipo = data.get('tipo')
        completado = data.get('completado')
        fecha_finalizacion = data.get('fecha_finalizacion')
        estado = data.get('estado')
        comple = 0
        if completado == True:
            comple = 1
        else:
            comple = 0

        print(data)

        titulos = ['Remitente', 'Tipo', 'Fecha de entrada', 'Fecha de finalizacion', 'Folio']
        campos = ['remitente', 'tipo', 'fecha_entrada', 'fecha_finalizacion', 'numero_folios']
        opciones = [remitente, tipo, fecha_entrada, fecha_finalizacion, numero_folios]
        cols = []
        fields = []
        datos_t = []
        aux = []
        datos_c = []

        for i, op in enumerate(opciones):
            if op == 1:
                cols.append(titulos[i])
                fields.append(campos[i])
                datos_t.append(titulos[i])
                #print(fields)
                #datos_t.append(titulos[i])

        rows = Expediente.objects.filter(Q(completado=comple), Q(fecha_entrada__range=(fecha_inicio,fecha_fin)))
        print(rows)
        if estado == 0:
            rows = Expediente.objects.filter(Q(completado=comple), Q(fecha_entrada__range=(fecha_inicio,fecha_fin)))
        elif estado == 1:
            rows = Expediente.objects.filter(Q(completado=comple), Q(fecha_entrada__range=(fecha_inicio,fecha_fin)),Q(estado__estado = str(estado)))
        elif estado == 2:
            rows = Expediente.objects.filter(Q(completado=comple), Q(fecha_entrada__range=(fecha_inicio,fecha_fin)),Q(estado__estado = str(estado)))
        elif estado == 3:
            rows = Expediente.objects.filter(Q(completado=comple), Q(fecha_entrada__range=(fecha_inicio,fecha_fin)),Q(estado__estado = str(estado)))

        rows.values_list(*fields)

        for row in rows:
            for col_num, elem in enumerate(fields):
                aux.append(str(row.get(elem)))
            datos_c.append(aux)
            aux = []

        datos = []
        datos.append(datos_t)

        for dat in datos_c:
            datos.append(dat)

        print(datos)
        fecha = datetime.now()
        nombre = "reporte_pdf" + str(fecha.year) + str(fecha.month) + str(fecha.day) + str(fecha.hour) + str(fecha.minute) + str(fecha.second) + ".pdf"
        path = settings.MEDIA_ROOT + nombre
        doc = SimpleDocTemplate(path, pagesize = A4)
        story=[]

        t = Table(datos, colWidths=102, rowHeights=20)
        t.setStyle([
                ('GRID',(0,0),(-1,-1),0.5,colors.grey),
                ('BOX',(0,0),(-1,-1),1,colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.white),
                ])

        story.append(t)
        story.append(Spacer(0,15))

        doc.build(story)
        #os.system(nombre)
        print(doc)

        url = settings.MEDIA_URL + nombre
        return self.create_response(request, {'url': url}, status=200)

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
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)

        exp = Expediente.objects.filter(id=id)
        obj = Requisito.objects.filter(expediente=exp)

        dd = []
        if obj.exists():
            for o in obj:
                d = {'id': o.id, 'requisito': o.requisito, 'cumplido': o.cumplido, 'expediente': o.expediente.id}
                dd.append(d)

        data = json.dumps(dd)

        return HttpResponse(data, content_type='application/json', status=200)

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

        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        t = request.META['HTTP_AUTHORIZATION']
        t = t[7:]

        token = AccessToken.objects.get(token=t)
        user = Usuario.objects.get(id=token.user.id)
        expediente = Expediente.objects.get(id=id)

        obs = data.get('observacion', ' ')

        observacion = Observacion(observacion=obs, expediente=expediente, usuario=user)
        observacion.save()

        return self.create_response(request, { "success": True}, HttpCreated)

    def informacion(self, request, id, **kwargs):
        self.method_check(request, allowed=['post', 'get'])
        self.is_authenticated(request)
        #self.is_authorized(request)

        exp = Expediente.objects.filter(id=id)
        obj = Observacion.objects.filter(expediente=exp)

        dd = []
        if obj.exists():
            for o in obj:
                d = {'observacion': o.observacion, 'expediente': o.expediente.id, 'usuario': o.usuario.username}
                dd.append(d)

        data = json.dumps(dd)

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

        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        #token = data.get('token', ' ')
        #fecha_recibido = data.get('fecha_recibido', ' ')
        #fecha_envio = data.get('fecha_envio', ' ')
        obs = data.get('observaciones', ' ')
        ide = data.get('enviado', ' ')
        idr = data.get('recibido', ' ')

        enviado = Usuario.objects.get(id=ide)
        recibido = Usuario.objects.get(id=idr)
        expediente = Expediente.objects.get(id=id)

        act = Actualizacion(observaciones=obs, expediente=expediente, enviado=enviado, recibido=recibido)
        act.save()

        expediente.leido = 0
        expediente.save()

        return self.create_response(request, { "success": True}, HttpCreated)

    def informacion(self, request, id, **kwargs):
        self.method_check(request, allowed=['get', 'post'])
        self.is_authenticated(request)
        #self.is_authorized(request)

        exp = Expediente.objects.filter(id=id)
        obj = Actualizacion.objects.filter(expediente=exp)

        dd = []
        if obj.exists():
            for o in obj:
                d = {'fecha_recibido': o.fecha_recibido, 'fecha_envio': o.fecha_envio, 'observacion': o.observaciones, 'enviado': o.enviado.username, 'recibido': o.recibido.username}
                dd.append(d)

        data = json.dumps(dd, cls=DjangoOverRideJSONEncoder)

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
