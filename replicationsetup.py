from io import StringIO
import sys
from middleware import RetryInterceptor
from client_library import LockClient
import time
import subprocess
import threading
import os
import signal
import lock_pb2
from logger import Logger
import grpc
from concurrent import futures
import lock_pb2_grpc
from server import LockService

def start_server(port,slave):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=100))
    lock_pb2_grpc.add_LockServiceServicer_to_server(LockService(drop=False,load=False,slave=slave,port=port[-5:]), server)
    server.add_insecure_port(port)
    server.start()
    print(f"Server started (localhost) on port {port}.")
    server.wait_for_termination()

def server1():
    s = start_server("127.0.0.1:56751",False)
    time.sleep(10)
    s.terminate()
def server2():
    s = start_server("127.0.0.1:56752",True)
    time.sleep(10)
    s.terminate()
def server3():
    s = start_server("127.0.0.1:56753",True)
    time.sleep(10)
    s.terminate()
def client1():
    client1 = LockClient(interceptor=RetryInterceptor())             
    client1.RPC_init()
    time.sleep(1)
    client1.RPC_lock_acquire()
    client1.RPC_append_file("file_1.txt", "A")
    client1.RPC_append_file("file_2.txt", "ayax")
    client1.RPC_append_file("file_3.txt", "test")
    client1.RPC_append_file("file_3.txt", "my")
    client1.RPC_append_file("file_2.txt", "name")
    client1.RPC_append_file("file_1.txt", "is")
    print("-------Client 1 lock release-------")
    client1.RPC_lock_release()
    time.sleep(15)
    p = subprocess.Popen (["rm", "-r","./filestore/56751"])
    p = subprocess.Popen (["rm", "-r","./filestore/56752"])
    p = subprocess.Popen (["rm", "-r","./filestore/56753"])


# 
thread1 = threading.Thread(target=server1)
thread2 = threading.Thread(target=server2)
thread3 = threading.Thread(target=server3)
thread4 = threading.Thread(target=client1)
thread1.start()
thread2.start()
thread3.start()
thread4.start()
thread1.join()
thread2.join()
thread3.join()
thread4.join()

#p.terminate()