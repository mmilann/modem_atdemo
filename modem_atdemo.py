#!/usr/bin/env python
# modem_demo.py - Python script demonstrates using AT commands to 
# communicate with Cellular Modem in order to connect with cloud,
# send/receive messages over TCP/IP or SMS and receive GPS/GLONASS 
# positioning data
#
# Author: Milan Neskovic, 2018
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

from time import sleep
import serial
import sys
from collections import deque

ser = None
at_result_codes = ['OK', 'CONNECT', 'RING', 'NO CARRIER', 'ERROR', 'NO DIALTONE', 'BUSY', 'NO ANSWER']

def AT_Command(cmd):
	ser.write(cmd+'\r') 
	sleep(0.1)
	rsp = {'result':'', 'info':'', 'command':''}
	ret = ser.readline()
	if ret == "\r\n" or ret == "":
		return rsp
	rsp['command'] = ret.split('\r')[0]
	ret = ser.readline()
	while ret:
		r = ret.split('\r')[0]
		if r in at_result_codes:
			rsp['result'] = r
			return rsp
		rsp['info'] = rsp['info'] + ret if ret != "\r\n" else rsp['info']
		ret = ser.readline()
	ret = ser.readline()
	if ret == "\r\n" or ret == "":
		return rsp
	rsp['result'] = ret.split('\r')[0]
	return rsp

def PrintInfo(cmd, cmdName):
	ret = AT_Command(cmd)
	if ret['result'] == 'OK': print cmdName + ':\n', ret['info']
	else: print 'AT Command: ',cmd , ', status: ', ret['result'], '\n'

def PrintNetworkInfo():
	PrintInfo('AT+COPS?', 'Operator')
	PrintInfo('AT+CREG?', 'Network registration')
	PrintInfo('AT+CSQ', 'RSSI') # get RSSI
	PrintInfo('AT+CGDCONT?', 'GPRS network registration status') # get GPRS network registration status
	PrintInfo('AT+CIPGSMLOC=1,1', 'GSM Loc') # get GSM Loc
	PrintInfo('AT+CPSI?', 'UE system information')

def Convert(coord):
    #Converts DDDMM.MMMMM -&gt; DD deg MM.MMMMM min
    x = coord.split(".")
    head = x[0]
    tail = x[1]
    deg = head[0:-2]
    min = head[-2:]
    return deg + " deg " + min + "." + tail + " min"

def GNSS_QuectelConfigure():
	if AT_Command('AT+QGPSEND')['result'] != 'OK': #Turn off GNSS
		print 'Failed to turn off GNSS'
	if AT_Command('AT+QGPSCFG="gpsnmeatype",3')['result'] != 'OK': # configure nmea type
		print 'Failed to configure GNSS nmea type'
	if AT_Command('AT+QGPSCFG="nmeasrc",1')['result'] != 'OK': # configure nmea source
		print 'Failed to configure GNSS nmea source'
	if AT_Command('AT+QGPS=1')['result'] != 'OK': # turn on
		print 'Failed to turn on GNSS'
	ret = AT_Command('AT+QGPSLOC=?') # get one reading
	if ret['result'] != 'OK': 
		print 'Failed to get GNSS reading'
	else:
		print ret['info']
	
def GNSS_SIMComConfigure():
	if AT_Command('AT+CGPS=0')['result'] != 'OK': #Turn off GNSS
		print 'Failed to turn off GNSS'  
	#AT_Command('AT+CGPSINFOCFG=10,31') # Report GPS NMEA-0183 sentence
	#AT_Command('AT+CGPSPMD=127') # Configure positioning mode
	if AT_Command('AT+CVAUXS=1')['result'] != 'OK': # turn on active antenna bias VDD_EXT
		print 'Failed to active GNSS antenna bias'
	# AT_Command('AT+CGPSCOLD') - Cold start GPS, AT_Command('AT+CGPSHOT') - Hot start GPS 
	if AT_Command('AT+CGPS=1')['result'] != 'OK': 
		print 'Failed to start GNSS'
	
def GNSS_HuaweiConfigure():
	AT_Command('AT^WPDOM=0') #Set the positioning method to Standalone
	AT_Command('AT^WPDST=0') #=0 - Set the session type to single positioning; =1 - set the session type to tracking and positioning.
	AT_Command('AT^WPQOS=255,500') #Set the positioning service quality. The first parameter indicates the response time, and the second indicates the horizontal accuracy threshold
	AT_Command('AT^WPDGP') #Start positioning.

def GNSS_QuectelRead():
	ret = AT_Command('AT+QGPSGNMEA="GGA"') # get one gps reading
	if ret['result'] != 'OK': 
		return {'error':'Failed to read GNSS data'}

	data = ret['info']
	#print ret['info']
	if len(data) < 10:
		return {'error':'Invalid GNSS data'}
		
	ret = {'error':'No Error'}
	sdata = data.split(":")[1].split(",")
	ret['time'] = sdata[1][0:2] + ":" + sdata[1][2:4] + ":" + sdata[1][4:6] if  sdata[1].strip() else ''
	ret['latitude'] = Convert(sdata[2]) if sdata[2] != '' else '' #latitude
	ret['latitude_dir'] = sdata[3] if  sdata[3] != '' else ''  #latitude direction N/S
	ret['longitute'] = Convert(sdata[4]) if  sdata[4] != '' else '' #longitute
	ret['longitute_dir'] = sdata[5] if  sdata[5] != '' else '' #longitude direction E/W
	ret['altitude'] = sdata[9] if  sdata[9] != '' else ''
	ret['speed'] = ""#sdata[14]       #Speed in knots
	ret['true_course'] = sdata[11] if  sdata[11] != '' else ''  #True course
	ret['date'] = ''#sdata[14][0:2] + "/" + sdata[14][2:4] + "/" + sdata[14][4:6] if  sdata[14] != '' else '' #date
	return ret

def GNSS_SIMComRead():
	rsp = AT_Command('AT+CGPSINFO') # get one gps reading
	if rsp['result'] != 'OK': 
		return {'error':'Failed to read GNSS data'}

	data = rsp['info']
	#print rsp['info']
	if len(data) < 10:
		return {'error':'Invalid GNSS data'}
		
	ret = {'error':'No Error'}
	sdata = data.split(":")[1].split(",")
	ret['latitude']  = Convert(sdata[0]) if  sdata[0].strip() else ''  #latitude
	ret['latitude_dir'] = sdata[1] if  sdata[1] != '' else ''     #latitude direction N/S
	ret['longitute'] = Convert(sdata[2]) if  sdata[2] != '' else ''  #longitute
	ret['longitute_dir'] = sdata[3] if  sdata[3] != '' else '' #longitude direction E/W
	ret['date'] = sdata[4][0:2] + "/" + sdata[4][2:4] + "/" + sdata[4][4:6] if  sdata[4] != '' else '' #date
	ret['time'] = sdata[5][0:2] + ":" + sdata[5][2:4] + ":" + sdata[5][4:6] if  sdata[5] != '' else ''
	ret['altitude'] = sdata[6] if  sdata[6] != '' else '' # altitude
	ret['speed'] = sdata[7] if  sdata[7] != '' else '' #Speed in knots
	ret['true_course'] = sdata[8] if  sdata[8] != '' else '' #True course
	return ret
	
def PrintPositioningData(data):
	print "time: %s, latitude: %s(%s), longitude: %s(%s), altitude: %s, speed: %s, True Course: %s, Date: %s" %  (
		data['time'],
		data['latitude'],
		data['latitude_dir'],
		data['longitute'],
		data['longitute_dir'],
		data['altitude'],
		data['speed'],
		data['true_course'],
		data['date']) 

def TCPIPClientSIMComSend(apn, address, port, packet):
	#print AT_Command('AT+CPIN?') # whether some password is required or not 
	#print AT_Command('AT+CSQ') # received signal strength
	#print AT_Command('AT+CREG?') # the registration of the ME
	#print AT_Command('AT+CGATT?')  # GPRS Service's status
	#print AT_Command('AT+CIPMODE?')
	#print AT_Command('AT+CPSI?')
	print AT_Command('AT+CGSOCKCONT=1,"IP","'+apn+'"') # Start task and set APN.
	print AT_Command('AT+CSOCKSETPN=1')
	print AT_Command('AT+NETOPEN')
	sleep(1)
	print AT_Command('AT+CIPOPEN=0,"TCP","'+address+'",'+port)  # TCP connect to server
	sleep(3)
	print AT_Command('AT+CIPSEND=0,'+str(len(packet))) # send data length
	ser.write(packet) # send packet
	print AT_Command('AT+CIPSEND: 0,0') # Query data is sent successfully
	print AT_Command('AT+CIPCLOSE=0')
		
def TCPIPClientQuectelSend(apn, address, port, packet):
	print AT_Command('AT+QICSGP=1,1,"'+apn+'","","",1') # Set Access Point Name (APN)
	print AT_Command('AT+QIACT=1') # Activate the APN network
	sleep(1)
	print AT_Command('AT+QIACT?') # Query the APN assigned IP address
	print AT_Command('AT+QIOPEN=1,0,"TCP","'+address+'",'+port+',0,1')  # Create a TCP connection to server
	sleep(3)
	print AT_Command('AT+QISEND=0,'+str(len(packet))) # send data length
	ser.write(packet) # send packet
	print AT_Command('AT+QISEND=0,0') # Query data is sent successfully
	print AT_Command('AT+QICLOSE=0')
	
def TCPIPServerSIMComSetup(apn, port):
	print AT_Command('AT+CGSOCKCONT=1,"IP","'+apn+'"') # Start task and set APN.
	#print AT_Command('AT+CSOCKSETPN=1')
	print AT_Command('AT+NETOPEN')
	sleep(1)
	ret = AT_Command('AT+IPADDR')
	if ret['result'] != 'OK':
		print 'Failed to query local IP address, ',  ret
		return False
	adr = ret['info'].split('\r')[0]
	ret = AT_Command('AT+SERVERSTART='+port+',0') # Create a TCP server
	if ret['result'] != 'OK':
		print 'Failed to start Server, ', adr, ret
		return False
	print 'Server started at local IP:', adr +':'+ port
	return True
	
def TCPIPServerQuectelSetup(apn, port):
	print AT_Command('AT+QICSGP=1,1,"'+apn+'","","",1') # Set Access Point Name (APN)
	print AT_Command('AT+QIACT=1') # Activate the APN network
	sleep(1)
	ret = AT_Command('AT+QIACT?')
	if ret['result'] != 'OK':
		print 'Failed to query local IP address, ',  ret
		return False
	adr = ret['info'].split(',')[3].split('\r')[0] if ret['info'] else ''
	ret = AT_Command('AT+QIOPEN=1,1,"TCP LISTENER","127.0.0.1",0,'+port+',0') # Create a TCP server
	if ret['result'] != 'OK':
		print 'Failed to start Server, ', adr, ret
		return False
	print 'Server started at local IP:', adr +':'+ port
	return True

def GetArgOptionValue(args, opt):
	i = args.index(opt) if opt in args else -1
	if (i > 0) and (len(args) > (i+1)) and (len(args[i+1].split('"')) == 1):
		return args[i+1].split('"')[0]
	else:
		return None
	
if __name__ == "__main__":
	args = sys.argv
	
	devPort = '/dev/ttyUSB2'
	p = GetArgOptionValue(args, '--port')
	if p:
		devPort = p
	else:
		print 'Device port not specified, using default:', devPort
		
	try:
		ser = serial.Serial(
			port=devPort,
			baudrate = 115200,
			parity=serial.PARITY_NONE,
			stopbits=serial.STOPBITS_ONE,
			bytesize=serial.EIGHTBITS, 
			timeout=1
		)
	except:
		print 'Failed to initialize device:', devPort, 'exiting...'
		sys.exit()
		
	#print AT_Command('AT+IPR=115200\r')  # set baud rate
	#print AT_Command('AT+IPREX=0\r') # simcom set autoboudrate
	#print AT_Command('AT+IFC=2,2\r')   # Enable UART flow control
	#print AT_Command('AT+CGFUNC=?\r')   # simcom get GPIO function

	ret = AT_Command('ATI') # Get modem identification information
	if ret['result'] == '':
		print 'Modem is not responding'
		sys.exit()
		
	imei = ret['info']
	print 'Modem information:\n' , imei
	
	if 'Quectel' in imei:
		print AT_Command('AT+QCFG="risignaltype","physical"') # Configure RI signal for ring/sms interrupt, when URC returns send 120ms pulse
		print AT_Command('AT+QCFG="urc/ri/smsincoming","pulse",200') # Configure RI Behavior When Incoming SMS URCs are Presented
		
	if '--gps' in args or '--gnss' in args:
	
		if 'Quectel' in imei:
			GNSS_QuectelConfigure()
			sleep(0.5)
			print 'Reading GNSS data:'
			while True:
				ret = GNSS_QuectelRead()
				if ret['error'] == 'No Error':
					PrintPositioningData(ret)
				else:
					print ret['error']
				sleep(5)
				
		elif 'SIMCOM' in imei:
			GNSS_SIMComConfigure()
			sleep(0.5)
			print 'Reading GNSS data:'
			while True:
				ret = GNSS_SIMComRead()
				if ret['error'] == 'No Error':
					PrintPositioningData(ret)
				else:
					print ret['error']
				sleep(5)
		else:
			print 'No Compatible Modem recognised'
			
	elif '--hologram-send' in args:
		message = GetArgOptionValue(args, '--hologram-send')
		if not message:
			print 'No message, exiting...'
			sys.exit()

		key = GetArgOptionValue(args, '--devicekey')
		if not key:
			print 'No device key specified, exiting...'
			sys.exit()

		packet = '{"k":"'+key+'","d":"'+message+'","t":"TOPIC1"}'
		if 'Quectel' in imei:
			TCPIPClientQuectelSend('hologram', '23.253.146.203', '9999', packet)
		elif 'SIMCOM' in imei:
			TCPIPClientSIMComSend('hologram', '23.253.146.203', '9999', packet)
		else:
			print 'No Compatible Modem recognised'
		
	elif '--hologram-receive' in args:
		if 'Quectel' in imei:
			TCPIPServerQuectelSetup('hologram', '2020')
			while True:
				str = ser.readline()
				if str and str != "\r\n":
					#print str 
					if '+QIURC: "recv"' in str:
						sockId = str.split(',')[1]
						ret = AT_Command('AT+QIRD='+sockId+',1500')
						if ret['result'] == 'OK':
							length = ret['info'].split(':')[1]
							data = ret['info'].split('\r\n')[1]
							print data
				sleep(0.5)
				
		elif 'SIMCOM' in imei:
			TCPIPServerSIMComSetup('hologram', '2020')
			print AT_Command('AT+CIPRXGET=2,1,1024') #  get data, this only needs to be set once
			lines = iq=deque(['']*3)
			while True:
				str = ser.readline()
				if str and str != "\r\n":
					lines.append(str)
					#print lines 
					if 'RECV FROM' in lines[1]:
						data = str
						print data, ', ', lines[1]
					lines.popleft()
				sleep(0.5)

		else:
			print 'No Compatible Modem recognised'
	elif '--sms-receive' in args:
		print AT_Command('AT+CMGF=1') # Set SMS system into text mode, as opposed to PDU mode. 
		print AT_Command('AT+CSDH=1') # Set text mode parameters, 1-show the values in result codes
		while True:
			str = ser.readline()
			if str and str != "\r\n":
				#print str 
				if '+CMTI:' in str:
					slot = str.split(',')[1]
					ret = AT_Command('AT+CMGR='+slot) # Send command to retrieve SMS message and parse line of response.
					if (ret['result'] == 'OK'):
						d = ret['info'].split(',')
						sender = d[1]
						msg = d[-1].split('\r\n')[1]
						print 'message received:', sender
						print msg
					else:
						print ret
			sleep(1)
	elif '--sms-send' in args:
		AT_Command('AT+CMGF=1') # Set SMS system into text mode
		num = GetArgOptionValue(args, '--number')
		ser.write('AT+CMGS="'+num+'"\r') 
		str = ''
		while not str:
			str = ser.readline()
		print str
		msg = GetArgOptionValue(args, '--sms-send')
		ser.write(msg+'\032') 
		str = ''
		while not str:
			str = ser.readline()
		print str
	else:
		PrintNetworkInfo()
