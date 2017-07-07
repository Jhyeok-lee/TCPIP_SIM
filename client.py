import sys
import socket
import select
import time
import threading
from threading import Timer
import random

class Client(threading.Thread):

	CLIENT_IP = ''
	SERVER_IP = ''
	NAME = 0
	PORT = 0

	BANDWIDTH = float(192)
	QDELAY = float(0.01)
	RECV_BUFFER = 192
	MSS = 192

	TCP_STATE = ''

	CLIENT_SOCKET = None
	SOCKET_LIST = []

	SEND_LOCK = threading.Lock()
	RECEIVE_LOCK = threading.Lock()
	RESEND_LOCK = threading.Lock()
	TIME_LOCK = threading.Lock()

	def __init__(self, client_ip, server_ip, port, name):
		super(Client, self).__init__()
		self.CLIENT_IP = client_ip
		self.SERVER_IP = server_ip
		self.PORT = port
		self.NAME = name

		medium_ip = '127.0.0.1'
		self.CLIENT_SOCKET = socket.socket()
		self.CLIENT_SOCKET.settimeout(2)

		try:
			self.CLIENT_SOCKET.connect( (medium_ip, self.PORT) )
			self.SOCKET_LIST.append( self.CLIENT_SOCKET )

		except:
			print("Unable to connect medium.")
			self.CLIENT_SOCKET.close()
			return

		print("%s Client : Connected to %d Medium" %(self.NAME, self.PORT) )
		print("%s Client : Try tcp-connect to %s server" %(self.NAME, self.SERVER_IP))
		self.TCP_STATE = 'CLOSED'

	TIMEOUT = float(1)
	SAMPLE_RTT = float(0)
	ESTIMATED_RTT = float(0)
	DEV_RTT = float(0)
	SEND_TIME = float(0)
	RECEIVE_TIME = float(0)
	SEND_DELAY = float(0.01)

	CWND = float(192)
	SSTHRESH = float(0)

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

	RECEIVE_BUFFER = []
	RECEIVE_BUFFER_SIZE = 100
	RECEIVE_BUFFER_COUNT = 0

	RESEND_BUFFER = {}
	RESEND_BUFFER_COUNT = 0

	ACK_RECEIVE_COUNT = 0
	TIMEOUT_COUNT = 0
	DUP_COUNT = 0

	def run(self):

		receiver = threading.Thread(target = self.receive_thread)
		sender = threading.Thread(target = self.send_thread)
		receiver.start()
		sender.start()
		time.sleep(0.1)

		#self.establish()
		#time.sleep(1)

		#self.initializaion()
		#time.sleep(1)

		ack_checker = threading.Thread(target = self.ack_check_thread)
		timeout_checker = threading.Thread(target = self.timeout_check_thread)
		ack_checker.start()

		self.test1()
		time.sleep(0.1)
		timeout_checker.start()

		time.sleep(60)
		self.print_result()

		#self.terminate()

		sys.exit()

	def test1(self):

		self.SEQ_NUM = random.randrange(0,1000)
		self.DATA = 10
		print("%d Client : Start SEQ(%d)" %(self.NAME, self.SEQ_NUM))
		time.sleep(1)

		self.set_send_time()

		for i in range(0, 100):

			send_packet = self.make_packet()
			self.input_send_buffer( send_packet )
			self.SEQ_NUM += self.DATA


	def establish(self):

		while self.TCP_STATE == 'CLOSED':

			self.SYN_BIT = 1
			self.SEQ_NUM = random.randrange(0, 1000)
			self.DATA = 1
			self.SEND_BASE = self.SEQ_NUM
			self.NEXT_SEQ_NUM = self.SEQ_NUM + self.DATA

			syn_packet = self.make_packet()

			self.SEND_TIME = time.time()
			self.input_send_buffer(syn_packet)
			self.TCP_STATE = 'SYN_SENT'
			print("%d Client : SYN_SENT" %self.NAME)

		while self.TCP_STATE == 'SYN_SENT':

			if time.time() - self.SEND_TIME > self.TIMEOUT:
				print("%d Client - Timeout" %self.NAME)
				self.SEND_TIME = time.time()
				self.input_send_buffer(syn_packet)
				self.TIMEOUT *= 2
				continue

			if self.RECEIVE_BUFFER_COUNT == 0:
				continue

			re = self.output_receive_buffer()

			self.SEQ_NUM = self.NEXT_SEQ_NUM
			self.ACK_NUM = re[2] + re[8]
			self.SYN_BIT = 0			
			self.RECEIVE_TIME = time.time()

			syn_packet = self.make_packet()
			self.input_send_buffer(syn_packet)
			self.TCP_STATE = 'ESTABLISHED'
			print("%d Client : ESTABLISHED" %self.NAME)

			return

	def terminate(self):

		while self.TCP_STATE == 'ESTABLISHED':

			self.SEQ_NUM = random.randrange(0, 1000)
			self.FIN_BIT = 1
			self.DATA = 1
			self.NEXT_SEQ_NUM = self.SEQ_NUM + self.DATA
			self.ACK_NUM = self.SEQ_NUM + self.DATA

			fin_packet = self.make_packet()

			self.input_send_buffer( fin_packet )

			self.TCP_STATE = 'FIN-WAIT1'
			print("%d Client : FIN-WAIT1" %self.NAME)

		while self.TCP_STATE == 'FIN-WAIT1':

			if self.RECEIVE_BUFFER_COUNT == 0:
				continue

			ack_packet = self.output_receive_buffer()

			if ack_packet[6] != 1:
				continue

			if ack_packet[3] != self.ACK_NUM:
				continue

			self.TCP_STATE = 'FIN-WAIT2'
			print("%d Client : FIN-WAIT2" %self.NAME)

		while self.TCP_STATE == 'FIN-WAIT2':

			if self.RECEIVE_BUFFER_COUNT == 0:
				continue

			fin_packet = self.output_receive_buffer()

			if fin_packet[4] != 1:
				continue

			self.SEQ_NUM = self.NEXT_SEQ_NUM
			self.ACK_NUM = ack_packet[2] + ack_packet[8]
			self.ACK_BIT = 1

			ack_packet = self.make_packet()

			self.input_send_buffer( ack_packet )

			self.TCP_STATE = 'CLOSED'
			print("%d Client : CLOSED" %self.NAME)

			sys.exit()


	def ack_check_thread(self):

		while 1:

			if self.RECEIVE_BUFFER_COUNT == 0:
				continue

			receive_packet = self.output_receive_buffer()
			self.set_receive_time()
			ack = receive_packet[3]
			seq = receive_packet[2]
			rwnd = receive_packet[7]

			if ack > self.SEND_BASE:

				self.TIME_LOCK.acquire()

				print("%d Client : ACK(%d) RWND(%d) Receive" %(self.NAME, ack, rwnd))
				self.SAMPLE_RTT = self.RECEIVE_TIME - self.SEND_TIME
				self.SEND_BASE = ack
				self.RWND = rwnd
				self.DUP_NUM = 0
				self.ACK_RECEIVE_COUNT += 1

				self.SEND_DELAY = 0.01 + 0.01*(100-self.RWND)

				if self.SSTHRESH == 0:
					self.CWND *= 2
					self.BANDWIDTH = self.CWND / self.SAMPLE_RTT
					print("%d Client : Exponential Increase Bandwidth(%f)" %(self.NAME, self.BANDWIDTH))
				elif self.SSTHRESH > self.CWND:
					self.CWND *= 2
					self.BANDWIDTH = self.CWND / self.SAMPLE_RTT
					print("%d Client : Exponential Increase Bandwidth(%f)" %(self.NAME, self.BANDWIDTH))
				elif self.SSTHRESH <= self.CWND:
					self.CWND += self.MSS
					self.BANDWIDTH = self.CWND / self.SAMPLE_RTT
					print("%d Client : Linear Increase Bandwidth(%d)" %(self.NAME, self.BANDWIDTH))

				self.remove_ack_received(ack)

				if self.RESEND_BUFFER_COUNT > 0:
					self.set_timeout_interval()
					self.set_send_time()

				self.TIME_LOCK.release()

			else:
				self.DUP_NUM += 1

				if( self.DUP_NUM == 3):

					try:
						self.DUP_NUM = 0
						re_send_packet = self.find_seq_sended(ack)
						self.DUP_COUNT += 1

						self.SSTHRESH = self.CWND/2
						self.CWND = self.SSTHRESH+3*self.MSS
						self.BANDWIDTH = self.CWND

						print("%d Client : Duplicated ACK - resend %d SEQ" %(self.NAME, re_send_packet[2]))
						self.input_send_buffer(ack)
					except:
						continue


	def timeout_check_thread(self):

		while 1:

			if self.RESEND_BUFFER_COUNT == 0:
				continue

			if time.time() - self.SEND_TIME > self.TIMEOUT:

				self.TIME_LOCK.acquire()

				try:
					least_seq_num = self.find_least_seq_num()
					packet = self.RESEND_BUFFER[ least_seq_num ]
				except:
					self.TIME_LOCK.release()
					continue

				if least_seq_num < self.SEND_BASE:
					self.TIME_LOCK.release()
					continue

				if packet[0] != self.CLIENT_IP:
					self.TIME_LOCK.release()
					continue

				if packet[1] != self.SERVER_IP:
					self.TIME_LOCK.release()
					continue

				self.input_send_buffer(packet)

				self.SSTHRESH = self.CWND/2
				self.CWND = self.MSS
				self.BANDWIDTH = self.CWND
				self.TIMEOUT_COUNT += 1
				self.TIMEOUT *= 2
				print("%d Client : Timeout - resend SEQ(%d), Slow Start@@@@@@@@@@@@" %(self.NAME, packet[2]))

				self.TIME_LOCK.release()


	def set_send_time(self):

		self.SEND_TIME = time.time()
		return


	def set_receive_time(self):

		self.RECEIVE_TIME = time.time()
		return

	def print_result(self):

		print("%d Client : ACK Receive - %d times" %(self.NAME, self.ACK_RECEIVE_COUNT))
		print("%d Client : Timeout - %d times" %(self.NAME, self.TIMEOUT_COUNT))
		print("%d Client : Duplicated ACK - %d times" %(self.NAME, self.DUP_COUNT))
		print(self.RESEND_BUFFER)
		print(self.RECEIVE_BUFFER)


	def set_timeout_interval(self):

		self.ESTIMATED_RTT = self.ESTIMATED_RTT*0.875 + self.SAMPLE_RTT*0.125
		self.DEV_RTT = self.DEV_RTT*0.75 + abs(self.SAMPLE_RTT - self.ESTIMATED_RTT)*0.25
		self.TIMEOUT = self.ESTIMATED_RTT + self.DEV_RTT*4

		print("%d Client : ACK Receive - Timeout interval set to %f" %(self.NAME, self.TIMEOUT) )
		return


	def find_least_seq_num(self):

		self.RESEND_LOCK.acquire()
		time.sleep(self.QDELAY)
		seq_num_list = self.RESEND_BUFFER.keys()
		self.RESEND_LOCK.release()

		return min(seq_num_list)

	def find_seq_sended(self, seq):

		self.RESEND_LOCK.acquire()
		time.sleep(self.QDELAY)
		packet = self.RESEND_BUFFER[seq]
		self.RESEND_LOCK.release()

		return packet


	def remove_ack_received(self, ack):

		self.RESEND_LOCK.acquire()
		time.sleep(self.QDELAY)
		seq_num_list = self.RESEND_BUFFER.keys()

		for i in seq_num_list:
			if i <= ack:
				del self.RESEND_BUFFER[i]

		self.RESEND_LOCK.release()

		return


	def make_packet(self):

		return [self.CLIENT_IP, self.SERVER_IP, self.SEQ_NUM, self.ACK_NUM,
							  self.FIN_BIT, self.SYN_BIT, self.ACK_BIT, self.RWND, self.DATA]


	def input_send_buffer(self, packet):

		self.SEND_LOCK.acquire()
		time.sleep(self.QDELAY)
		self.SEND_BUFFER.append(packet)
		self.SEND_BUFFER_COUNT += 1
		self.SEND_LOCK.release()

		return


	def output_receive_buffer(self):

		self.RECEIVE_LOCK.acquire()
		time.sleep(self.QDELAY)
		packet = self.RECEIVE_BUFFER.pop(0)
		self.RECEIVE_BUFFER_COUNT -= 1
		self.RECEIVE_LOCK.release()

		return packet


	def receive_thread(self):

		while 1:
			ready_to_read, ready_to_write, in_error = select.select(self.SOCKET_LIST, [], [])
			for sock in ready_to_read:
				if sock == self.CLIENT_SOCKET:

					if self.RECEIVE_BUFFER_COUNT == self.RECEIVE_BUFFER_SIZE:
						print("%d Client : receive buffer full" %self.NAME)
						time.sleep(2)
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

			if list_packet[0] != self.CLIENT_IP:
				continue

			if list_packet[1] != self.SERVER_IP:
				continue

			self.RESEND_LOCK.acquire()
			time.sleep(self.QDELAY)
			self.RESEND_BUFFER[ list_packet[2] ] = list_packet
			self.RESEND_BUFFER_COUNT += 1
			self.RESEND_LOCK.release()

			string_packet = self.make_string( list_packet )

			time.sleep( len(string_packet)/self.BANDWIDTH )
			time.sleep( self.SEND_DELAY )
			self.CLIENT_SOCKET.send( string_packet )


	def initializaion(self):

		self.TIMEOUT = float(1)
		self.SAMPLE_RTT = float(0)
		self.ESTIMATED_RTT = float(0)
		self.DEV_RTT = float(0)
		self.SEND_TIME = float(0)
		self.RECEIVE_TIME = float(0)
		self.SEND_DELAY = float(0.01)

		self.BANDWIDTH = float(192)
		self.SSTHRESH = float(0)
		self.CWND = self.MSS

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

		self.RECEIVE_BUFFER = []
		self.RECEIVE_BUFFER_SIZE = 100
		self.RECEIVE_BUFFER_COUNT = 0

		self.RESEND_BUFFER = {}
		self.RESEND_BUFFER_COUNT = 0

		self.ACK_RECEIVE_COUNT = 0
		self.TIMEOUT_COUNT = 0
		self.DUP_COUNT = 0

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