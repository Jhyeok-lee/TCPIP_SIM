import client
import server
import medium
import time

def main():

	m1 = medium.Medium(1, 9998)
	m1.start()
	time.sleep(0.1)

	s1 = server.Server('192.168.0.1', '192.168.0.2', 9998, 1)
	s2 = server.Server('192.168.0.3', '192.168.0.4', 9998, 2)
	s3 = server.Server('192.168.0.5', '192.168.0.6', 9998, 3)

	c1 = client.Client('192.168.0.1', '192.168.0.2', 9998, 1)
	c2 = client.Client('192.168.0.3', '192.168.0.4', 9998, 2)
	c3 = client.Client('192.168.0.5', '192.168.0.6', 9998, 3)

	s1.start()
	time.sleep(0.1)
	s2.start()
	time.sleep(0.1)
	s3.start()
	c1.start()
	time.sleep(0.1)
	c2.start()
	time.sleep(0.1)
	c3.start()

if __name__ == '__main__':
	main()