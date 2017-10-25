import random

class Generador ():

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
        return "EXP" + str(id)
