# Much of this code is adapted from Adafruit's BlueFruit Low Level Example code
#   Original code can be found here: 
#   https://github.com/adafruit/Adafruit_Python_BluefruitLE/blob/master/examples/low_level.py
# The Adafruit Library is licensed under the MIT license.

from badge_connection import *

import logging
import time
import uuid
import sys
import threading

#import Adafruit_BluefruitLE
#from platform import *
from bluepy import *
from bluepy import btle
from bluepy.btle import UUID, Peripheral, DefaultDelegate, AssignedNumbers ,Scanner
from bluepy.btle import BTLEException
import struct	

logger = logging.getLogger(__name__)

# Enable debug output.
# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

# Define service and characteristic UUIDs used by the UART service.
UART_SERVICE_UUID = uuid.UUID('6E400001-B5A3-F393-E0A9-E50E24DCCA9E')
TX_CHAR_UUID      = uuid.UUID('6E400002-B5A3-F393-E0A9-E50E24DCCA9E')
RX_CHAR_UUID      = uuid.UUID('6E400003-B5A3-F393-E0A9-E50E24DCCA9E')


class ScanDelegate(DefaultDelegate):

	def __init__(self):
		DefaultDelegate.__init__(self)


	def handleDiscovery(self, dev, isNewDev, isNewData):
		pass


class SimpleDelegate(DefaultDelegate):

    def __init__(self, bleconn):
        DefaultDelegate.__init__(self)
        self.bleconn = bleconn

    def handleNotification(self, cHandle, data):
        print(repr(data))
        self.bleconn.received(data)



# BLEBadgeConnection represents a connection to 'ble_device', a badge connected over BLE.
#    ('ble_device' should be a device from the Bluefruit Library)
# This class implements the BadgeConnection interface to communicate with
#   a badge over the BLE UART service using the Adafruit BlueFruit Library.
# This class implements an additional class method, BLEBadgeConnection.get_connection_to_badge(), 
#   that can be used to retrieve an instance of this class that represents a connection to a badge with
#   the given ID. This class method should be the main way clients instantiate new BLEBadgeConnections.
class BLEBadgeConnection(BadgeConnection):
	
	def __init__(self, ble_device):
		self.ble_device = ble_device

		# We will set these on connection to be the correct objects from the
		#   Adafruit library.
		self.uart = None
		self.rx = None
		self.tx = None
		self.conn = None

		# Contains the bytes recieved from the device. Held here until an entire message is recieved.
		self.rx_buffer = ""
		# Condition used to synchronize waiting for the reciept of a message between threads.
		# This condition is held when someone is waiting on a message to come in and is notified 
		# after an entire message is recieved.
		self.rx_condition = threading.Condition()
		# Set to be the recieved message when an entire message is recieved.
		self.rx_message = None
		# The number of bytes in the completed message we are currently waiting on.
		self.rx_bytes_expected = 0

		BadgeConnection.__init__(self)

	# Returns a BLEBadgeConnection() to the first badge it sees, or none if a badge
	#   could not be found in timeout_seconds seconds. (Default is 10)
	@classmethod
	def get_connection_to_badge(cls, device_addr, timeout_seconds=10.0):
		
		#scanner = Scanner().withDelegate(ScanDelegate())
		#devices = scanner.scan(timeout_seconds)

		#for dev in devices:
		#	if (dev.addr==device_addr):
		#		print(dev.addr,"is found!")
				

		return cls(device_addr)

	# Function to receive RX characteristic changes.  Note that this will
	# be called on a different thread so be careful to make sure state that
	# the function changes is thread safe.  Use Queue or other thread-safe
	# primitives to send data to other threads.
	#def received(self,data):
	#	logger.debug("Recieved {}".format(data.encode("hex")))
	#	self.rx_buffer += data
	#	if len(self.rx_buffer) >= self.rx_bytes_expected:
	#		#self.on_message_rx(self.rx_buffer[0:self.rx_bytes_expected])
	#		conn.setDelegate(SimpleDelegate(bleconn=self))
	#		self.conn.waitForNotifications(5.0)
	#		self.rx_buffer = self.rx_buffer[self.rx_bytes_expected:]
	#		self.rx_bytes_expected = 0

			#if len(self.rx_buffer) > 0:
			#	logger.debug("RX Buffer: {}".format(self.rx_buffer.encode("hex")))
			#	raise BufferError("Got unexcpeted rx bytes.")


	def received(self,data):
		logger.debug("Recieved {}".format(data.encode("hex")))
		self.rx_message = data
		#if len(self.rx_buffer) >= self.rx_bytes_expected:
			#self.on_message_rx(self.rx_buffer[0:self.rx_bytes_expected])
			#self.rx_buffer = self.rx_buffer[self.rx_bytes_expected:]
			#self.rx_bytes_expected = 0


	# Implements BadgeConnection's connect() spec.	
	def connect(self):
		#self.ble_device.connect()
		#print(self.ble_device)
		self.conn = btle.Peripheral(self.ble_device, btle.ADDR_TYPE_RANDOM)
		
		logger.debug("Attempting to discover characteristics...")

		#self.ble_device.discover([UART_SERVICE_UUID], [TX_CHAR_UUID, RX_CHAR_UUID])
		#conn = btle.Peripheral(self.ble_device, btle.ADDR_TYPE_RANDOM)

		# Find the UART service and its characteristics.
		self.uart = self.conn.getServiceByUUID(UART_SERVICE_UUID)
		self.rx = self.uart.getCharacteristics(RX_CHAR_UUID)[0]
		self.tx = self.uart.getCharacteristics(TX_CHAR_UUID)[0]



		# Turn on notification of RX characteristics using the callback above.
		logger.debug('Subscribing to RX characteristic changes...')
		
		#self.rx.write(struct.pack('<bb',0x01,0x00)) # doesn't work. not sure why
		#conn.writeCharacteristic(handle=self.rx.getHandle(),val=struct.pack('<bb', 0x00, 0x00))
		CONFIG_HANDLE = 0x000c;
		self.conn.writeCharacteristic(handle=CONFIG_HANDLE,val=struct.pack('<bb', 0x01, 0x00))
		self.conn.setDelegate(SimpleDelegate(bleconn=self))

		#conn.waitForNotifications(1.0)


		# Adafruit's PyOBJ bindings have a race condition in them, where they set the notification state 
		# but don't wait for the notification state to actually change before writing things.
		# A sleep here will suffice, but if I'm super nice I oughta submit a PR to them to fix that for them.
		#import time
		#time.sleep(1)
		#self.conn = conn


	# Implements BadgeConnections's disconnect() spec.
	def disconnect(self):
		
		self.uart = None
		self.tx = None
		self.rx = None

		self.rx_buffer = ""
		self.rx_condition = threading.Condition()
		self.rx_message = None
		self.rx_bytes_expected = 0

		#self.ble_device.disconnect()
		self.conn.disconnect()
		self.ble_device = None

	# Implements BadgeConnection's is_connected() spec.
	def is_connected(self):

		if (self.ble_device == None):
			return False
		else:
			return True

	# Implements BadgeConnection's await_data() spec.
	def await_data(self, data_len):
		if not self.is_connected():
			raise RuntimeError("BLEBadgeConnection not connected before await_data()!")

		self.rx_bytes_expected = data_len
		if data_len > 0:
			self.conn.waitForNotifications(5.0)
			#self.rx_condition.acquire()
			#with self.rx_condition:
				#self.rx_condition.wait()


			#self.rx_condition.notify()
			return self.rx_message

	# Implements BadgeConnection's send() spec.
	def send(self, message, response_len=0):
		if not self.is_connected():
			raise RuntimeError("BLEBadgeConnection not connected before send()!")

		print(self.ble_device)
		self.rx_bytes_expected = response_len
		self.tx.write(message,withResponse=True)
		
		if response_len > 0:
			self.conn.waitForNotifications(5.0)
			#with self.rx_condition:
			#	self.rx_condition.wait(5.0)
	
			return self.rx_message

	# Internal method called when a full message has been recieved from the badge. 
	# Notifies anyone waiting on data from the badge that the recieved message is ready.
	#def on_message_rx(self, message):
	#	self.rx_message = message
	#	self.received(self.rx_message)


		#if message > 0:
		#	self.conn.waitForNotifications(5.0)
		#with self.rx_condition:
		#	#self.rx.waitForNotifications(5.0)
		#	time.sleep(1)
		#	self.rx_condition.notifyAll()
