import random
import socket
import time
from threading import Event, Thread

WORDS = ('air', 'owl', 'way', 'hen', 'pan', 'owe', 'few', 'kid', 'see', 'beg', 'act', 'cow', 'bin', 'pit', 'ice', 'far')


def pick_words():
    count = random.randint(1, 10)
    words = random.choices(WORDS, k=count)
    return " ".join(words).encode() + b'\n'


class ThreadListener(Thread):
    def __init__(self, connection):
        super().__init__()
        self.terminate_event = Event()
        self.connection = connection

    def run(self):
        with self.connection:
            print('Connected by', addr)
            while not self.terminate_event.is_set():
                words = pick_words()
                conn.sendall(words)
                print("Sending {}".format(words))
                time.sleep(0.5)
        print("Thread is over")


if __name__ == '__main__':
    print("Starting something")
    threads = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('0.0.0.0', 9999))
            s.listen(100)
            print("Listening for connections...")
            while True:
                conn, addr = s.accept()
                print("Accepted connection from ", addr)
                thread = ThreadListener(conn)
                thread.start()
                threads.add(thread)
    except Exception as e:
        print(e)
        print("Terminating threads")
        for thread in threads:
            thread.terminate_event.set()
        for thread in threads:
            thread.join(5)
