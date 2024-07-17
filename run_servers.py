import os
from multiprocessing import Process

def start_django():
    os.system('python manage.py runserver')

def start_tcp_server():
    os.system('python tcp_server.py')

if __name__ == '__main__':
    p1 = Process(target=start_django)
    p2 = Process(target=start_tcp_server)

    p1.start()
    p2.start()

    p1.join()
    p2.join()
