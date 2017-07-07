import sys
import socket
import select
import time
import threading
from threading import Timer
import random

class Server(threading.Thread):

	CLIENT_IP = ''
	SERVER_IP = ''
	NAME = 0
	PORT = 0

	BANDWIDTH = float(100000)
	QDELAY = float(0.1)
	RECV_BUFFER = 192

	TCP_STATE = ''

	SERVER_SOCKET = None
	SOCKET_LIST = []

	SEND_LOCK = threading.Lock()
	RECEIVE_LOCK = threading.Lock()

	def __init__(self, client_ip, server_ip, port, name):
		super(Server, self).__init__()
		self.CLIENT_IP = client_ip
		self.SERVER_IP = server_ip
		self.PORT = port
		self.NAME = name

		medium_ip = '127.0.0.1'
		self.SERVER_SOCKET = socket.socket()
		self.SERVER_SOCKET.settimeout(2)

		try:
			self.SERVER_SOCKET.connect( (medium_ip, self.PORT) )
			self.SOCKET_LIST.append( self.SERVER_SOCKET )

		except:
			print("Unable to connect medium.")
			self.SERVER_SOCKET.close()
			return

		print("%s server & %d medium connected" %(self.SERVER_IP, self.PORT) )
		print("%s server try tcp-connect to %s client" %(self.SERVER_IP, self.CLIENT_IP))
		self.TCP_STATE = 'LISTEN'

	TIMEOUT = float(1)
	SAMPLE_RTT = float(0)
	ESTIMATED_RTT = float(1)
	DEV_RTT = float(0)
	SEND_TIME = float(0)
	RECEIVE_TIME = float(0)
	SEND_DELAY = float(0)

	SEND_BASE = 0
	NEXT_SEQ_NUM = 0
	DUP_NUM = 0

	SEQ_NUM = 0		#2
	ACK_NUM = 0		#3
	FIN_BIT = 0		#4
	SYN_BIT = 0		#5
	ACK_BIT = 0		#6
	RWND = 0		#7
	DATA = 0		#8

	SEND_BUFFER = []
	SEND_BUFFER_SIZE = 100
	SEND_BUFFER_COUNT = 0
	LAST_SEND = 0

	RECEIVE_BUFFER = []
	RECEIVE_BUFFER_SIZE = 100
	RECEIVE_BUFFER_COUNT = 0

	def run(self):

		receiver = threading.Thread(target = self.receive_thread)
		sender = threading.Thread(target = self.send_thread)
		receiver.start()
		time.sleep(0.1)
		sender.start()
		time.sleep(0.1)
		#time.sleep(1)

		#self.establish()
		#time.sleep(1)

		#self.initializaion()
		#time.sleep(1)

		ack_sender = threading.Thread(target = self.sending_ack_thread)
		ack_sender.start()

		#self.terminate()


	def sending_ack_thread(self):

		self.SEQ_NUM = random.randrange(0, 1000)

		while(1):

			if self.RECEIVE_BUFFER_COUNT == 0:
				continue

			receive_packet = self.output_receive_buffer()
			seq = receive_packet[2]
			data = receive_packet[8]

			if receive_packet[0] != self.CLIENT_IP:
				continue

			if receive_packet[1] != self.SERVER_IP:
				continue

			if seq+data > self.ACK_NUM:
				self.ACK_NUM = seq + data

			self.RWND = self.RECEIVE_BUFFER_SIZE - self.RECEIVE_BUFFER_COUNT
			self.ACK_BIT = 1
			self.DATA = 1

			#print("%d Server : Receive SEQ(%d), DATA(%d)" %(self.NAME, seq, data))
			#print("%d Server : Sending ACK(%d), SEQ(%d), RWND(%d)" %(self.NAME, self.SEQ_NUM, self.ACK_NUM, self.RWND))

			ack_packet = self.make_packet()
			self.input_send_buffer( ack_packet )

			self.SEQ_NUM += self.DATA


	def establish(self):

		while self.TCP_STATE == 'LISTEN':

			if self.RECEIVE_BUFFER_COUNT == 0:
				continue

			syn_packet = self.output_receive_buffer()

			if syn_packet[5] != 1:
				continue

			self.TCP_STATE = 'SYN_RCVD'
			self.SEQ_NUM = random.randrange(0, 1000)
			self.ACK_NUM = syn_packet[2] + syn_packet[8]
			self.RWND = self.RECEIVE_BUFFER_SIZE - self.RECEIVE_BUFFER_COUNT
			self.ACK_BIT = 1
			self.DATA = 1

			self.NEXT_SEQ_NUM = self.SEQ_NUM + self.DATA

			ack_packet = self.make_packet()
			self.input_send_buffer( ack_packet )
			print("%d server set to SYN_RCVD" %self.NAME)
			break

		while self.TCP_STATE == 'SYN_RCVD':

			if self.RECEIVE_BUFFER_COUNT == 0:
				continue

			syn_packet = self.output_receive_buffer()

			if syn_packet[3] != self.NEXT_SEQ_NUM:
				continue

			self.TCP_STATE = 'ESTABLISHED'
			print("%d server set to ESTABLISHED" %self.NAME)

		return

	def terminate(self):

		while self.TCP_STATE == 'ESTABLISHED':

			if self.RECEIVE_BUFFER_COUNT == 0:
				continue

			fin_packet = self.output_receive_buffer()

			if fin_packet[4] != 1:
				continue

			self.SEQ_NUM = random.randrange(0, 1000)
			self.ACK_NUM = fin_packet[2] + fin_packet[8]
			self.ACK_BIT = 1

			ack_packet = self.make_packet()

			self.input_send_buffer( ack_packet )

			self.TCP_STATE = 'CLOSE-WAIT'
			print("%d SERVER : CLOSE-WAIT" %self.NAME)

		while self.TCP_STATE == 'CLOSE-WAIT':

			time.sleep(3)

			self.SEQ_NUM = random.randrange(0, 1000)
			self.FIN_BIT = 1
			self.ACK_BIT = 1
			self.DATA = 1
			self.NEXT_SEQ_NUM = self.SEQ_NUM + self.DATA

			fin_packet = self.make_packet()

			self.input_send_buffer( fin_packet )

			self.TCP_STATE = 'LAST-ACK'
			print("%d SERVER : LAST-ACK" %self.NAME)

		while self.TCP_STATE == 'LAST-ACK':
			
			if self.RECEIVE_BUFFER_COUNT == 0:
				continue

			ack_packet = self.output_receive_buffer()

			self.TCP_STATE = 'CLOSED'
			print("%d SERVER : CLOSED" %self.NAME)
			sys.exit()


	def make_packet(self):
		return [self.CLIENT_IP, self.SERVER_IP, self.SEQ_NUM, self.ACK_NUM,
							  self.FIN_BIT, self.SYN_BIT, self.ACK_BIT, self.RWND, self.DATA]


	def output_receive_buffer(self):

		self.RECEIVE_LOCK.acquire()
		time.sleep(self.QDELAY)
		packet = self.RECEIVE_BUFFER.pop(0)
		self.RECEIVE_BUFFER_COUNT -= 1
		self.RECEIVE_LOCK.release()

		return packet


	def input_send_buffer(self, packet):

		self.SEND_LOCK.acquire()
		time.sleep(self.QDELAY)
		self.SEND_BUFFER.append(packet)
		self.SEND_BUFFER_COUNT += 1
		self.SEND_LOCK.release()


	def receive_thread(self):

		while 1:
			ready_to_read, ready_to_write, in_error = select.select(self.SOCKET_LIST, [], [])
			for sock in ready_to_read:
				if sock == self.SERVER_SOCKET:

					if self.RECEIVE_BUFFER_COUNT == self.RECEIVE_BUFFER_SIZE:
						print("%d Server : receive buffer full" %self.NAME)
						continue

					string_packet = sock.recv( self.RECV_BUFFER )
					list_packet = self.make_list( string_packet )

					if list_packet[0] != self.CLIENT_IP:
						continue

					if list_packet[1] != self.SERVER_IP:
						continue

					self.RECEIVE_LOCK.acquire()
					time.sleep(self.QDELAY)
					self.RECEIVE_BUFFER.append( list_packet )
					self.RECEIVE_BUFFER_COUNT += 1
					self.RECEIVE_LOCK.release()
						

	def send_thread(self):

		while 1:

			if self.SEND_BUFFER_COUNT == 0:
				continue

			self.SEND_LOCK.acquire()
			time.sleep(self.QDELAY)
			list_packet = self.SEND_BUFFER.pop(0)
			self.SEND_BUFFER_COUNT -= 1
			self.SEND_LOCK.release()

			string_packet = self.make_string( list_packet )

			time.sleep( len(string_packet)/self.BANDWIDTH )
			time.sleep( self.SEND_DELAY )
			self.SERVER_SOCKET.send( string_packet )


	def initializaion(self):

		self.TIMEOUT = float(1)
		self.SAMPLE_RTT = float(0)
		self.ESTIMATED_RTT = float(1)
		self.DEV_RTT = float(0)
		self.SEND_TIME = float(0)
		self.RECEIVE_TIME = float(0)
		self.SEND_DELAY = float(0)

		self.SEND_BASE = 0
		self.NEXT_SEQ_NUM = 0
		self.DUP_NUM = 0

		self.SEQ_NUM = 0		#2
		self.ACK_NUM = 0		#3
		self.FIN_BIT = 0		#4
		self.SYN_BIT = 0		#5
		self.ACK_BIT = 0		#6
		self.RWND = 0		#7
		self.DATA = 0		#8

		self.SEND_BUFFER = []
		self.SEND_BUFFER_SIZE = 100
		self.SEND_BUFFER_COUNT = 0
		self.LAST_SEND = 0

		self.RECEIVE_BUFFER = []
		self.RECEIVE_BUFFER_SIZE = 100
		self.RECEIVE_BUFFER_COUNT = 0


	#packet_list = [0:CLIENT_IP, 1:SERVER_IP, 2:SEQ_NUM, 3:ACK_NUM, 4:FIN, 5:SYN, 6:ACK, 7:RWND, 8:DATA]

	def make_string(self, packet_list):

		i_source_ip = packet_list[0]
		i_source_ip = i_source_ip.split('.')
		i_source_ip1 = str(bin(int(i_source_ip[0])))[2:]
		i_source_ip2 = str(bin(int(i_source_ip[1])))[2:]
		i_source_ip3 = str(bin(int(i_source_ip[2])))[2:]
		i_source_ip4 = str(bin(int(i_source_ip[3])))[2:]

		i_destination_ip = packet_list[1]
		i_destination_ip = i_destination_ip.split('.')
		i_destination_ip1 = str(bin(int(i_destination_ip[0])))[2:]
		i_destination_ip2 = str(bin(int(i_destination_ip[1])))[2:]
		i_destination_ip3 = str(bin(int(i_destination_ip[2])))[2:]
		i_destination_ip4 = str(bin(int(i_destination_ip[3])))[2:]

		i_sequence_number = str(bin(packet_list[2]))[2:]
		i_acknowledgment_number = str(bin(packet_list[3]))[2:]
		i_fin_bit = str(packet_list[4])
		i_syn_bit = str(packet_list[5])
		i_ack_bit = str(packet_list[6])
		i_padding = '0000000000000'
		i_rwnd = str(bin(packet_list[7]))[2:]
		i_data = str(bin(packet_list[8]))[2:]

		packet_string = ''
		packet_string += (8-len(i_source_ip1))*'0' + i_source_ip1
		packet_string += (8-len(i_source_ip2))*'0' + i_source_ip2
		packet_string += (8-len(i_source_ip3))*'0' + i_source_ip3
		packet_string += (8-len(i_source_ip4))*'0' + i_source_ip4
		packet_string += (8-len(i_destination_ip1))*'0' + i_destination_ip1
		packet_string += (8-len(i_destination_ip2))*'0' + i_destination_ip2
		packet_string += (8-len(i_destination_ip3))*'0' + i_destination_ip3
		packet_string += (8-len(i_destination_ip4))*'0' + i_destination_ip4
		packet_string += (32-len(i_sequence_number))*'0' + i_sequence_number
		packet_string += (32-len(i_acknowledgment_number))*'0' + i_acknowledgment_number
		packet_string += i_fin_bit
		packet_string += i_syn_bit
		packet_string += i_ack_bit
		packet_string += i_padding
		packet_string += (16-len(i_rwnd))*'0' + i_rwnd
		packet_string += (32-len(i_data))*'0' + i_data

		return packet_string


	def make_list(self, packet_string):

		r_source_ip1 = int(packet_string[0:8], 2)
		r_source_ip2 = int(packet_string[8:16], 2)
		r_source_ip3 = int(packet_string[16:24], 2)
		r_source_ip4 = int(packet_string[24:32], 2)
		r_source_ip = str(r_source_ip1)
		r_source_ip += '.' + str(r_source_ip2)
		r_source_ip += '.' + str(r_source_ip3)
		r_source_ip += '.' + str(r_source_ip4)

		r_destination_ip1 = int(packet_string[32:40], 2)
		r_destination_ip2 = int(packet_string[40:48], 2)
		r_destination_ip3 = int(packet_string[48:56], 2)
		r_destination_ip4 = int(packet_string[56:64], 2)
		r_destination_ip = str(r_destination_ip1)
		r_destination_ip += '.' + str(r_destination_ip2)
		r_destination_ip += '.' + str(r_destination_ip3)
		r_destination_ip +=	'.' + str(r_destination_ip4)

		r_sequence_number = int(packet_string[64:96], 2)
		r_acknowledgment_number = int(packet_string[96:128], 2)
		r_fin_bit = int(packet_string[128])
		r_syn_bit = int(packet_string[129])
		r_ack_bit = int(packet_string[130])
		r_padding = packet_string[131:144]
		r_rwnd = int(packet_string[144:160], 2)
		r_data = int(packet_string[160:192], 2)

		packet_list = [r_source_ip, r_destination_ip, r_sequence_number, r_acknowledgment_number, r_fin_bit,
						r_syn_bit, r_ack_bit, r_rwnd, r_data]

		return packet_list