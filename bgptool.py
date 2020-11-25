import telnetlib
import ipaddress
from datetime import datetime
from datetime import date
import smtplib
import configparser
import re

AS=""                     #AS que debe estar en el aspath
ID=""                     #Para diferenciar si tienes varias instancias corriendo
MAILS=""                  #Direcciones de envío de mail

def carga_rangos(fichero):
    try:
        with open(fichero, "r") as f:
            lista_rangos=[]
            #print ("---------------Load ranges from",fichero,"---------------")
            for linea in f:
                try:
                    ip = ipaddress.IPv4Network(linea[:-1]) # para quitar el retorno de carro
                    #print(ip, "it is a correct network")
                    lista_rangos.append(linea[:-1]) 
                except ValueError:
                    print(linea, "it is a incorrect network. Not loaded")
            #print ("---------------Loaded Ranges---------------")
            return lista_rangos
    except (OSError, IOError) as e:
        print ("---------------No ranges to load---------------")
        return list()   

def carga_config():
    global MAILS
    global ID
    global AS
    config = configparser.ConfigParser()
    try:
        with open ('bgptool.ini') as f:  #Falta gestionar si un id no existe en el fichero
            config.read_file(f)
            if 'ID' in config['default']:
                ID=config['default']['ID']
            if 'MAILS' in config['default']:
                MAILS=config['default']['MAILS'].split(sep=',')
            if 'AS' in config['default']:
                AS=config['default']['AS']


    except (OSError, IOError) as e:
        print ("No configuration file")



def envia_correo(asunto, mensaje):
    remitente = "david.hernandezc@gmail.com"
    destinatario = MAILS
    asunto="BGPTOOL: " + ID + " " + asunto
    #print("EMAIL with subject-->", asunto)
    email = """From: %s
To: %s
MIME-Version: 1.0
Content-type: text/html
Subject: %s
    
%s
""" % (remitente, destinatario, asunto, mensaje)
    try:
        smtp = smtplib.SMTP('localhost')
        smtp.sendmail(remitente, MAILS, email)
        #print ("Email sent succesfully")
    except:
        print ("Error: we canot send the email<BR>")



LOGIN = "rviews"
PASSWORD = "rviews"
HOST = "route-server.ip.att.net"
COMANDO1="show route " 
COMANDO2= """ exact | match "AS pa" | no-more """
COMANDO3="""show route aspath-regex ".* 12430 .*"| match \* | no-more """ #AS no de la config aun
carga_config()
rangos=carga_rangos("rangos.txt")
log=""
hora = datetime.now()
log="-------------Start time: " + str(hora) + "-------------<BR>\n BGPTOOL " + ID + " "+ str(len(rangos))+" Ranges <BR><BR><BR>\n"
texto2="""<TABLE BORDER="1"> <TR><TH>RANGE</TH><TH>STATUS</TH><TH>AS PATH</TH></TR>"""
log=log+texto2
texto2=""



tn = telnetlib.Telnet(HOST,23)
tn.read_until(b"login:")
tn.write(LOGIN.encode('ascii') + b"\n")
tn.read_until(b":")
tn.write(PASSWORD.encode('ascii') + b"\n")
tn.read_until(b"att.net>")
tn.write(b"set cli screen-width 200\n")
tn.read_until(b"att.net>")
fallo=0

for rango in rangos:
    COMANDO=COMANDO1+rango+COMANDO2
    tn.write(COMANDO.encode('ascii')+ b"\n")
    result=tn.read_until(b"att.net>")
    lista_result=result.splitlines()
    rango_ok=0
    for line in lista_result:
        if "AS path" in str(line):
            rango_ok=1
            break
    if rango_ok==1:
        aspath=re.findall("\d+", str(line))
        if AS in aspath:
            #print (rango + " Routed: ", aspath)
            texto2="<TR><TD>" + rango + " </TD><TD>Routed</TD><TD>" + str(aspath) + "</TD></TR>"
        else:
            #print ("ALERT: " + rango + " Routed, but not in our AS: ", aspath)
            texto="ALERT: " + rango + " Routed, but not in our AS: " + str(aspath)
            texto2="""<TR bgcolor="red"><TD>"""  + rango + "</TD><TD>Routed, but not in our AS</TD><TD>" + str(aspath) + "</TD></TR>"
            fallo+=1
            #envia_correo(texto, texto2) mejor lo enviamos al final

    else:
        #print ("ALERT: " + rango + " NOT Routed")
        texto="ALERT: " + rango + " NOT Routed"
        texto2="""<TR bgcolor="red"><TD>"""  + rango + "</TD><TD>NOT Routed</TD></TR>"
        fallo+=1
        #envia_correo(texto, texto2) mejor lo enviamos al final
    log=log+texto2

log=log+"</TABLE>"

tn.write(COMANDO3.encode('ascii')+ b"\n")
result=tn.read_until(b"att.net>")
lista_result=result.splitlines()

prefijos_antes=-1
try:
    with open("num_prefijos.txt", "r") as fichero_prefijos:
        prefijos_antes=fichero_prefijos.read()
except(OSError, IOError) as e:
        print ("No hay fichero de prefijos")
prefijos=[]
for line in lista_result:
    linea=str(line)
    palabras=linea.split(' ')
    prefijos.append(palabras[0][2:])
prefijos_ahora=len(prefijos)
diferencia_de_rutas=prefijos_ahora-int(prefijos_antes)

texto="<br><br>Numero de rutas enrutadas por el AS12430: "+ str(prefijos_ahora)
log=log+texto
texto="<br><br>Numero de rutas enrutadas por el AS12430 la muestra anterior: "+ str(prefijos_antes)
log=log+texto
print("Numero de rutas enrutadas por el AS12430: "+ str(prefijos_ahora))
print("Numero de rutas enrutadas por el AS12430 la muestra anterior: " + str(prefijos_antes))
with open("num_prefijos.txt", "w") as fichero_prefijos:
    fichero_prefijos.write(str(prefijos_ahora))

hora_fin = datetime.now()
texto2="<br><br><br>-------------End time: " + str(hora_fin) + "-------------<BR>\n"
log=log +texto2
if (fallo>0):
    envia_correo("FAIL IN " + str(fallo) + " RANGE(S)",log)
if ((diferencia_de_rutas>100) or (diferencia_de_rutas<-100)):
    envia_correo("Cambio brusco de " + str(diferencia_de_rutas) + " prefijos con respecto a la muestra anterior",log)
if ((hora.hour==0)and(hora.minute<5)):  
    envia_correo("Daily report",log)



logfile=open("ultimo.html", "w")
print (log, file=logfile)
logfile.close()
logfile=open("lista_prefijos.txt", "a")
for prefijo in prefijos:
    print(str(hora_fin)+" "+ str(prefijo), file=logfile)
logfile.close()
tn.write(b"exit\n")






