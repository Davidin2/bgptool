import telnetlib
import ipaddress
from datetime import datetime
from datetime import date
import smtplib
import configparser
import re
import sys
import json

AS=""                     #AS que debe estar en el aspath
ID=""                     #Para diferenciar si tienes varias instancias corriendo
MAILS=""                  #Direcciones de envío de mail
PREFIX_DIFF=0            #diferencia de prefijos para mandar mail en valor absoluto

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
    global PREFIX_DIFF
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
            if 'PREFIX_DIFF' in config['default']:
                PREFIX_DIFF=config['default']['PREFIX_DIFF']

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
""" % (remitente, ",".join(destinatario), asunto, mensaje)
    try:
        smtp = smtplib.SMTP('localhost')
        smtp.sendmail(remitente, MAILS, email)
        #print ("Email sent succesfully")
    except:
        print ("Error: we canot send the email "+str(asunto)+"<br>")



LOGIN = "rviews"
PASSWORD = "Rviews"
HOST = "route-server.ip.tdc.net"
COMANDO1="show route " 
COMANDO2= """ exact | match "AS pa" | no-more """
COMANDO3="""show route aspath-regex ".* """ 
COMANDO4=""" .*"| match \* | no-more """
carga_config()
rangos=carga_rangos("rangos.txt")
log=""
hora = datetime.now().replace(microsecond=0)
log="-------------Start time: " + str(hora) + "-------------<BR>\n BGPTOOL " + ID + " "+ str(len(rangos))+" Ranges <BR><BR><BR>\n"
texto2="""<TABLE BORDER="1"> <TR><TH>RANGE</TH><TH>STATUS</TH><TH>AS PATH</TH></TR>"""
log=log+texto2
texto2=""



try:
    tn = telnetlib.Telnet(HOST,23,5)
except:
    ca=str(datetime.now().replace(microsecond=0))
    print (ca+" Fallo de conexion en el telnet")

result=tn.read_until(b"login:",6)
if ("login" not in str(result)):
    ca=str(datetime.now().replace(microsecond=0))
    print (ca+" Fallo esperando login")
    sys.exit(1)

tn.write(LOGIN.encode('ascii') + b"\n")
result=tn.read_until(b":",60)
if (":" not in str(result)):
    ca=str(datetime.now().replace(microsecond=0))
    print (ca+" Fallo esperando password")
    sys.exit(1)
tn.write(PASSWORD.encode('ascii') + b"\n")
result=tn.read_until(b".net>",60)
if ("net>" not in str(result)):
    ca=str(datetime.now().replace(microsecond=0))
    print (ca+" Fallo esperando prompt1")
    sys.exit(1)

tn.write(b"set cli screen-width 200\n")
result=tn.read_until(b".net>",60)
if ("net>" not in str(result)):
    ca=str(datetime.now().replace(microsecond=0))
    print (ca+" Fallo esperando prompt2")
    sys.exit(1)
fallo=0

data = {}
data["BGPTOOL: " + ID] = []


for rango in rangos:
    COMANDO=COMANDO1+rango+COMANDO2
    tn.write(COMANDO.encode('ascii')+ b"\n")
    result=tn.read_until(b".net>",60)
    if ("net>" not in str(result)):
        ca=str(datetime.now().replace(microsecond=0))
        print (ca+" Fallo esperando comando+2")
        sys.exit(1)
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
            data["BGPTOOL: " + ID].append({
                'range': rango,
                'Status': 'Routed',
                'aspath': str(aspath)})
            texto2="<TR><TD>" + rango + " </TD><TD>Routed</TD><TD>" + str(aspath) + "</TD></TR>"
        else:
            #print ("ALERT: " + rango + " Routed, but not in our AS: ", aspath)
            texto="ALERT: " + rango + " Routed, but not in our AS: " + str(aspath)
            data["BGPTOOL: " + ID].append({
                'range': rango,
                'Status': 'Routed, but not in our AS',
                'aspath': str(aspath)})
            texto2="""<TR bgcolor="red"><TD>"""  + rango + "</TD><TD>Routed, but not in our AS</TD><TD>" + str(aspath) + "</TD></TR>"
            fallo+=1
            #envia_correo(texto, texto2) mejor lo enviamos al final

    else:
        #print ("ALERT: " + rango + " NOT Routed")
        texto="ALERT: " + rango + " NOT Routed"
        data["BGPTOOL: " + ID].append({
                'range': rango,
                'Status': 'NOT Routed',
                'aspath': ""})
        texto2="""<TR bgcolor="red"><TD>"""  + rango + "</TD><TD>NOT Routed</TD></TR>"
        fallo+=1
        #envia_correo(texto, texto2) mejor lo enviamos al final
    log=log+texto2

with open('ultimo.json', 'w') as file:
    json.dump(data, file, indent=4)

log=log+"</TABLE>"
COMANDO5=COMANDO3 + str(AS) + COMANDO4
tn.write(COMANDO5.encode('ascii')+ b"\n")
result=tn.read_until(b".net>",60)
if ("net>" not in str(result)):
    ca=str(datetime.now().replace(microsecond=0))
    print (ca+" Fallo esperando comando5")
    sys.exit(1)
lista_result=result.splitlines()

num_prefijos_antes=-1
lista_prefijos_antes=[]
try:
    with open("num_prefijos.txt", "r") as fichero_prefijos:
        for linea in fichero_prefijos:
            lista_prefijos_antes.append(linea[:-1])
        num_prefijos_antes=lista_prefijos_antes[0]
except(OSError, IOError) as e:
        print ("There is no files with last prefix sample")

lista_prefijos_ahora=[]
for line in lista_result:
    linea=str(line)
    palabras=linea.split(' ')
    lista_prefijos_ahora.append(palabras[0][2:])
num_prefijos_ahora=len(lista_prefijos_ahora)
diferencia_de_rutas=num_prefijos_ahora-int(num_prefijos_antes)

texto="<br><br>Routed routes in AS" + str(AS)+ " : " + str(num_prefijos_ahora)
log=log+texto
texto="<br><br>Last sample Routed routes in AS" + str(AS)+ " : " + str(num_prefijos_antes)
log=log+texto
print("Routed routes in AS" + str(AS)+ " : " + str(num_prefijos_ahora))
print("Last sample Routed routes in AS" + str(AS)+ " : " + str(num_prefijos_antes))
with open("num_prefijos.txt", "w") as fichero_prefijos:
    fichero_prefijos.write(str(num_prefijos_ahora)+"\n")
    for prefijo in lista_prefijos_ahora:
        fichero_prefijos.write(str(prefijo)+"\n")

no_esta_ahora=[]
no_estaba_antes=[]

for prefijo_antes in lista_prefijos_antes:
    if "/" in str(prefijo_antes):
        if prefijo_antes not in lista_prefijos_ahora:
            no_esta_ahora.append(prefijo_antes)
for prefijo_ahora in lista_prefijos_ahora:
    if "/" in str(prefijo_ahora):
        if prefijo_ahora not in lista_prefijos_antes:
            no_estaba_antes.append(prefijo_ahora)
print("These prefixes were before and now they are not:")
print(no_esta_ahora)
print("These prefixes are now and they were not before:")
print(no_estaba_antes)

texto="<br><br>These prefixes were before and now they are not: " + str(no_esta_ahora)
log=log+texto
texto="<br><br>These prefixes are now and they were not before: " + str(no_estaba_antes)
log=log+texto



hora_fin = datetime.now().replace(microsecond=0)
texto2="<br><br><br>-------------End time: " + str(hora_fin) + "-------------<BR>\n"
log=log +texto2
if (fallo>0):
    envia_correo("FAIL IN " + str(fallo) + " RANGE(S)",log)
if ((diferencia_de_rutas>int(PREFIX_DIFF)) or (diferencia_de_rutas<-int(PREFIX_DIFF))):
    envia_correo("Sudden change of  " + str(diferencia_de_rutas) + " prefixes from the previous sample",log)
if ((hora.hour==0)and(hora.minute<5)):  
    envia_correo("Daily report",log)



logfile=open("ultimo.html", "w")
print (log, file=logfile)
logfile.close()
logfile=open("lista_prefijos.txt", "a")
for prefijo in lista_prefijos_ahora:
    print(str(hora_fin)+" "+ str(prefijo), file=logfile)
logfile.close()

logfile=open("lista_cambios.txt", "a")
for prefijo in no_esta_ahora:
    print(str(hora_fin)+" - "+ str(prefijo), file=logfile)
for prefijo in no_estaba_antes:
    print(str(hora_fin)+" + "+ str(prefijo), file=logfile)

logfile.close()

tn.write(b"exit\n")


#Posibles mejoras:
#¿Añadir los as a la lista de prefijos?




