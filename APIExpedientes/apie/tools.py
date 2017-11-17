import random
import datetime
import time
from django.core.serializers.json import DjangoJSONEncoder
import decimal
from django.utils.timezone import is_aware

class DjangoOverRideJSONEncoder(DjangoJSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time and decimal types.
    """
    def default(self, o):
        # See "Date Time String Format" in the ECMA-262 specification.
        if isinstance(o, datetime.datetime):
            r = o.isoformat(' ')
            if o.microsecond:
                r = r[:23] + r[26:]
            if r.endswith('+00:00'):
                r = r[:-6]
            return r
        elif isinstance(o, datetime.date):
            return o.isoformat(' ')
        elif isinstance(o, datetime.time):
            if is_aware(o):
                raise ValueError("JSON can't represent timezone-aware times.")
            r = o.isoformat(' ')
            if o.microsecond:
                r = r[:12]
            return r
        elif isinstance(o, decimal.Decimal):
            return str(o)
        else:
            return super(DjangoOverRideJSONEncoder, self).default(o)

def generar_clave(self):
    clave = ""

    no_vector = 0
    posicion = 0

    array_numeros = ([0,1,2,3,4,5,6,7,9])
    array_minusculas = "abcdefghijklmnopqrstuvwxyz"
    array_mayusculas = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    for i in range(30):
        no_vector = random.randint(0,2)
        if no_vector ==0:
            posicion = random.randint(0,8)
            clave = clave + str(array_numeros[posicion])
        elif no_vector == 1:
            posicion = random.randint(0, 25)
            clave = clave + array_minusculas[posicion]
        else:
            posicion = random.randint(0, 25)
            clave = clave + array_mayusculas[posicion]

    return clave

def codigo(self,id):
    cod = ""

    if id < 10:
        cod = "EXP00"+ str(id)
    elif id < 100:
        cod = "EXP0" + str(id)
    else:
        cod = "EXP" + str(id)
    return cod

def validarFecha(fecha):
    """
    Funcion para validar una fecha en formato:
        dd/mm/yyyy, dd/mm/yy, d/m/yy, dd/mm/yyyy hh:mm:ss, dd/mm/yy hh:mm:ss, d/m/yy h:m:s
    """
    for format in ['%Y-%m-%d', '%y-%m-%d', '%Y-%m-%d %H:%M:%S', '%y-%m-%d %H:%M:%S']:
        print "simon"
        try:
            print "aja"
            res = time.strptime(fecha, format)
            print "ok"
            return True
        except ValueError:
            return False
