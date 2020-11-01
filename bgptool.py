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
carga_config()
rangos=carga_rangos("rangos.txt")
log=""
hora = datetime.now()
log="Actual Date: " + str(hora) + " BGPTOOL: " + ID + "<BR>\n"
texto=log
texto2=""



tn = telnetlib.Telnet(HOST,23)
tn.read_until(b"login:")
tn.write(LOGIN.encode('ascii') + b"\n")
tn.read_until(b":")
tn.write(PASSWORD.encode('ascii') + b"\n")
tn.read_until(b"att.net>")
tn.write(b"set cli screen-width 200\n")
tn.read_until(b"att.net>")

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
            print (rango + " Routed: ", aspath)
            texto2=rango + " Routed: " + str(aspath)
        else:
            print ("ALERT: " + rango + " Routed, but not in our AS: ", aspath)
            texto="ALERT: " + rango + " Routed, but not in our AS: " + str(aspath)
            texto2="""<p style="color:#FF0000";>ALERT: """  + rango + " Routed, but not in our AS: " + str(aspath) + "</p>"
            envia_correo(texto, texto2)
    else:
        print ("ALERT: " + rango + " NOT Routed")
        texto="ALERT: " + rango + " NOT Routed"
        texto2="""<p style="color:#FF0000";>ALERT: """  + rango + " NOT Routed</p>"
        envia_correo(texto, texto2)
    log=log+texto2+"<br>\n"

if hora.hour==0:
    envia_correo("Daily report",log)
print(log)

tn.write(b"exit\n")






