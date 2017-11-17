"""APIExpedientes URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from tastypie.api import Api

from apie.resources import ExpedienteResource, RequisitoResource, ObservacionResource, ActualizacionResource, UsuarioResource, RolResource, EstadoResource

api_ = Api(api_name="expedientes")
api_.register(ExpedienteResource())
api_.register(RequisitoResource())
api_.register(ObservacionResource())
api_.register(ActualizacionResource())
api_.register(UsuarioResource())
api_.register(RolResource())
api_.register(EstadoResource())

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^', include(api_.urls)),
    url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
]
