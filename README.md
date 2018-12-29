# modem_atdemo
Python script for Linux demonstrates how to use low level AT commands to communicate with Cellular Modem,  send/receive messages over TCP/IP or SMS or receive GPS/GLONASS positioning data.

Install:
git clone https://github.com/mmilann/modem_atdemo.git
cd modem_atdemo

Example print modem network info with USB connected modem:
python modem_atdemo.py

or print info with modem connected to UART serial port:
python modem_atdemo.py --port "/dev/serial0"

Example send message to hologram cloud:
python modem_atdemo.py --hologram-send "Hello World" --devicekey "t>Wo>Tsg"

Example receive message from hologram cloud:
python modem_atdemo.py --port "/dev/serial0" --hologram-receive

Example receive SMS message with modem connected to UART serial port:
python modem_atdemo.py --port "/dev/serial0" --sms-receive

Example get GNSS positioning data:
python modem_atdemo.py --gnss
