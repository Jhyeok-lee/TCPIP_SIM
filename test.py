import threading
import time

class test(threading.Thread):
	"""docstring for test"""

	a = 0
	b = 0
	c = threading.Lock()

	def __init__(self):
		super(test, self).__init__()
		
	def good(self):
		
		time.sleep(0.0001)
		self.c.acquire()
		self.a = 2
		self.c.release()
		print(self.a)
		

	def love(self):
		
		self.c.acquire()
		self.a = 5
		self.c.release()
		print(self.a)
		


	def run(self):
		aa = threading.Thread(target = self.good)
		bb = threading.Thread(target = self.love)
		aa.start()
		bb.start()

q = test()
q.start()
