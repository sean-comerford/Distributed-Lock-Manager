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



# Test 1 Packet Delay

def test1():
    open("file_1.txt", 'w').close()
    p = subprocess.Popen(["python", "server.py",])
    time.sleep(1)
    client= LockClient(interceptor=RetryInterceptor())
    client2 = LockClient(interceptor=RetryInterceptor())
    capturedOutput = StringIO()
    sys.stdout = capturedOutput                  
    client.RPC_init()
    client2.RPC_init()
    client.RPC_lock_acquire()
    client2.RPC_lock_acquire(   )
    time.sleep(3)
    status = client.RPC_append_file("A.txt", "Hello",test=True)                          
    sys.stdout = sys.__stdout__       
    p.terminate()           
    assert open("file_1.txt", 'r').read() == ""
    print(status)
    assert status ==lock_pb2.Status.LOCK_EXPIRED
    
    print("TEST 1 PASSED")
# test1()

# Test 2: Packet Drop
def test2():
    open("file_1.txt", 'w').close()
    p = subprocess.Popen (["python", "server.py","-d","1"])
    time.sleep(1)
    def client1_behaviour():
        client= LockClient(interceptor=RetryInterceptor())
        client.RPC_init()
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "A")
    def client2_behaviour():
        client= LockClient(interceptor=RetryInterceptor())
        time.sleep(0.1)
        client.RPC_init()
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "B")
        client.RPC_lock_release()
    thread1 = threading.Thread(target=client1_behaviour)
    thread2 = threading.Thread(target=client2_behaviour)

    # Start the threads
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()
    p.terminate()
    assert open("file_1.txt", 'r').read() == "BA"


    # part b
    print("TEST 2)a) PASSED")
    open("file_1.txt", 'w').close()
    p = subprocess.Popen (["python", "server.py","-d","2"])
    time.sleep(1)
    def client1_behaviour():
        client= LockClient(interceptor=RetryInterceptor())
        client.RPC_init()
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "A")
    def client2_behaviour():
        client= LockClient(interceptor=RetryInterceptor())
        time.sleep(0.1)
        client.RPC_init()
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "B")
        client.RPC_lock_release()
    thread1 = threading.Thread(target=client1_behaviour)
    thread2 = threading.Thread(target=client2_behaviour)

    # Start the threads
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()
    p.terminate()
    assert open("file_1.txt", 'r').read() == "AB"
    print("TEST 2)b) PASSED")
    print("TEST 2 PASSED")

def testLog():
    logger = Logger()
    open("file_1.txt", 'w').close()
    p = subprocess.Popen (["python", "server.py"])
    time.sleep(1)
    def client1_behaviour():
        client= LockClient(interceptor=RetryInterceptor())
        client.RPC_init()
        client.RPC_lock_acquire()
        client.RPC_lock_release()
    def client2_behaviour():
        client= LockClient(interceptor=RetryInterceptor())
        time.sleep(0.1)
        client.RPC_init()
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "B")
        client.RPC_lock_release()
    thread1 = threading.Thread(target=client1_behaviour)
    thread2 = threading.Thread(target=client2_behaviour)

    # Start the threads
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()
    p.terminate()
    lock_owner, lock_counter, response_cache,client_counter,locked = logger.load_log()
    assert lock_owner == None
    assert lock_counter == 2
    assert locked == False
    assert client_counter == 2
    print("TEST LOG PASSED")
    
def testLog2():
    logger = Logger()
    open("file_1.txt", 'w').close()
    os.remove("log_server_1.json")
    p = subprocess.Popen(["python", "server.py"])
    time.sleep(1) 
    
    def client1_behaviour():
        client = LockClient(interceptor=RetryInterceptor())
        client.RPC_init()
        client.RPC_lock_acquire()
        client.RPC_lock_release()

    def client2_behaviour():
        client = LockClient(interceptor=RetryInterceptor())
        time.sleep(0.1)
        client.RPC_init()
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "B")
        client.RPC_lock_release()

    thread1 = threading.Thread(target=client1_behaviour)
    thread2 = threading.Thread(target=client2_behaviour)

    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()

    p.terminate()
    p = subprocess.Popen(["python", "server.py","-l","1"])
    
    lock_owner, lock_counter, response_cache,client_counter,locked = logger.load_log()
    assert lock_owner == None
    assert lock_counter == 2
    assert locked == False
    assert client_counter == 2
    print("TEST LOG2 PASSED")

testLog2()
