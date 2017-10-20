from django.db import IntegrityError
from django.contrib.auth import authenticate, login, logout
from django.db.models import signals
from django.conf.urls import url

from tastypie.resources import ModelResource, Resource
from tastypie.serializers import Serializer
from tastypie.authorization import DjangoAuthorization, ReadOnlyAuthorization, Authorization
from tastypie.authentication import BasicAuthentication, ApiKeyAuthentication
from tastypie.exceptions import BadRequest
from tastypie.http import HttpUnauthorized, HttpForbidden
from tastypie.utils import trailing_slash
from tastypie.constants import ALL
from tastypie.models import ApiKey, create_api_key
from tastypie.api import Api
from tastypie import fields

from oauth2_provider.models import AccessToken, Application
from datetime import date

from models import Registro, Usuario
from authentication import (OAuth20Authentication, OAuth2ScopedAuthentication)

import datetime
'''
class GrupoResource(ModelResource):
    class Meta:
        queryset = Grupo.objects.all()
        methods = ['post', 'get']
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
'''
signals.post_save.connect(create_api_key, sender=Usuario)
class UsuarioResource(ModelResource):
    #rol = fields.ForeignKey(GrupoResource, 'rol')
    class Meta:
        queryset = Usuario.objects.all()
        authorization = Authorization()
        #authentication = ApiKeyAuthentication()
        excludes = ['email', 'password', 'is_active', 'is_staff', 'is_superuser']
        filtering = {
            'username': ALL,
        }
        serializer = Serializer(formats=['json'])
        resource_name = 'user'

    def obj_create(self, bundle, request=None, **kwargs):
        try:
            bundle = super(UsuarioResource, self).obj_create(bundle)
            bundle.obj.set_password(bundle.data.get('password'))
            bundle.obj.save()
            self.user = Usuario.objects.get(codigo=bundle.data.get('codigo'))

            self.scopes = ("read", "write", "read write")
            for scope in self.scopes:
                scope_attrbute_name = "token_" + scope.replace(" ", "_")
                setattr(self, scope_attrbute_name, "TOKEN" + scope)
            self.token = 'TOKEN'
            self.scoped_token = self.token_read_write

            ot_application = Application(
                user = self.user,
                redirect_uris = 'https://127.0.0.1:8000',
                client_type = Application.CLIENT_CONFIDENTIAL,
                authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
                name = 'connection'
            )
            ot_application.save()

            for scope in self.scopes + (None,):
                options = {
                    'user': self.user,
                    'application': ot_application,
                    'expires': datetime.datetime.now() + datetime.timedelta(days=10),
                    'token': self.token
                }
                if scope:
                    scope_attrbute_name = "token_" + scope.replace(" ", "_")
                    options.update({
                        'scope': scope,
                        'token': getattr(self, scope_attrbute_name)
                    })
                ot_access_token = AccessToken(**options)
                ot_access_token.save()

        except IntegrityError:
            raise BadRequest('El usuario ya existe')

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
                    key = ApiKey.objects.get(user=user)
                except ApiKey.DoesNotExist:
                    return self.create_response(request, {'success': False, 'reason': 'missing key',}, HttpForbidden)

                ret = self.create_response(request, {'success': True, 'user': user, 'key':key.key})
                return ret
            else:
                return self.create_response(request, {'success': False, 'reason': 'disabled',}, HttpForbidden)
        else:
            return self.create_response(request, {'success': False, 'reason': 'incorrect', 'skip_login_redir':True}, HttpUnauthorized)

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
        authentication = OAuth20Authentication()
        serializer = Serializer(formats=['json'])
        resource_name = 'reg'
