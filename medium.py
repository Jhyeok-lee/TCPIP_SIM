import sys
import socket
import select
import time
import threading
import random
from threading import Timer

class Medium(threading.Thread):

	IP = ''
	PORT = 0
	NAME = 0
	COST = 0

	PDELAY = 0.01
	RECV_BUFFER = 192
	MEDIUM_SOCKET = None
	NUMBER_OF_NODES = 10
	STATUS = 'IDLE'
	SOCKET_LIST = []
	HOST_LIST = []

	BUFFER = {}

	def __init__(self, name, port):
		super(Medium, self).__init__()

		self.NAME = name
		self.PORT = port
		self.COST = random.randrange(0,10)

		self.MEDIUM_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.MEDIUM_SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.MEDIUM_SOCKET.bind( (self.IP, self.PORT) )
		self.MEDIUM_SOCKET.listen( self.NUMBER_OF_NODES )
		self.SOCKET_LIST.append( self.MEDIUM_SOCKET )

		print("%d Medium : Ready." %self.NAME)

	def run(self):

		while 1:

			ready_to_read, ready_to_write, exception = select.select( self.SOCKET_LIST, [], [], 0)

			for sock in ready_to_read:

				if sock == self.MEDIUM_SOCKET:
					connection_socket, addr = self.MEDIUM_SOCKET.accept()
					self.SOCKET_LIST.append( connection_socket )

				else:
					try:
						packet = sock.recv( self.RECV_BUFFER )
						if packet:

							if self.STATUS == 'IDLE':
								#print("Port %d medium is worked" %self.PORT)
								self.change_status()
								t = Timer(self.PDELAY, self.send_packet, (sock, packet))
								t.start()

							elif self.STATUS == 'BUSY':
								#print("Port %d medium is busy." %self.PORT)
								if packet in self.BUFFER:
									self.BUFFER[packet] += 1
								else:
									self.BUFFER[packet] = 1

								if self.BUFFER[packet] >= 6:
									K = random.randrange(0, pow(2,8))
								else:
									K = random.randrange(0, pow(2, self.BUFFER[packet]+2))

								t = Timer(K*self.PDELAY, self.send_packet, (sock, packet))
								t.start()

						else:
							if sock in self.SOCKET_LIST:
								print("Node (%s, %s) is disconnected" %sock.getpeername() )
								self.SOCKET_LIST.remove( sock )
								continue

					except:
						continue

						#if sock in self.SOCKET_LIST:
						#	print("Node (%s, %s) is error" %sock.getpeername() )
						#	self.SOCKET_LIST.remove( sock )
						#	continue


		return 0

	def send_packet(self, sender_socket, packet):

		for receiver_socket in self.SOCKET_LIST:
			if receiver_socket != self.MEDIUM_SOCKET :
				if receiver_socket != sender_socket :

						receiver_socket.send( packet )

		self.change_status()

	def medium_exit(self):

		for i in range(0, len(self.SOCKET_LIST) ):
			self.SOCKET_LIST[i].close()

	def change_status(self):

		if self.STATUS == 'IDLE':
			self.STATUS = 'BUSY'

		elif self.STATUS == 'BUSY':
			self.STATUS = 'IDLE'
