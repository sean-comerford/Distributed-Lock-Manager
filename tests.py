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


# Test A Packet Delay

def testA():
    
    p = subprocess.Popen(["python", "testserver.py","-d","5","-p","56751"])
    p2 = subprocess.Popen(["python", "server.py","-p","56752"])
    p3 = subprocess.Popen(["python", "server.py","-p","56753"])
    open("./filestore/56751/file_1.txt", 'w').close()
    time.sleep(1)
    def client1_behaviour():
        client= LockClient(interceptor=RetryInterceptor())
        client.RPC_init()
        client.RPC_lock_acquire()
        status = client.RPC_append_file("file_1.txt", "A",test=True)  
        time.sleep(5)
        print(f"Status: {status}")
        assert status ==lock_pb2.Status.LOCK_EXPIRED
        print("-------------STATUS CODE CORRECT------------")
    def client2_behaviour():
        client2 = LockClient(interceptor=RetryInterceptor())             
        client2.RPC_init()
        time.sleep(0.1)
        client2.RPC_lock_acquire()
    thread1 = threading.Thread(target=client1_behaviour)
    thread2 = threading.Thread(target=client2_behaviour)

    # Start the threads
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()
    p.terminate()
    
                            
    sys.stdout = sys.__stdout__       
    p.terminate()  
    p2.terminate()
    p3.terminate()
    assert open("./filestore/56751/file_1.txt", 'r').read() == ""
   
    
    print("TEST 1 PASSED")


# Test B: Packet Drop
def testB():
    p = subprocess.Popen(["python", "testserver.py","-d","1","-p","56751"])
    p2 = subprocess.Popen(["python", "server.py","-p","56752"])
    p3 = subprocess.Popen(["python", "server.py","-p","56753"])
    open("./filestore/56751/file_1.txt", 'w').close()
    time.sleep(1)
    def client1_behaviour():
        client= LockClient(interceptor=RetryInterceptor())
        client.RPC_init()
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "A")
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
    p2.terminate()
    p3.terminate()
    assert open("./filestore/56751/file_1.txt", 'r').read() == "BA"


    # part b
    print("TEST b)a) PASSED")
    
    p = subprocess.Popen (["python", "testserver.py","-d","2","-p","56751"])
    p2 = subprocess.Popen(["python", "server.py","-p","56752"])
    p3 = subprocess.Popen(["python", "server.py","-p","56753"])
    open("./filestore/56751/file_1.txt", 'w').close()
    time.sleep(1)
    def client1_behaviour():
        client= LockClient(interceptor=RetryInterceptor())
        client.RPC_init()
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "A")
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
    p2.terminate()
    p3.terminate()
    assert open("./filestore/56751/file_1.txt", 'r').read() == "AB"
    print("TEST 1)b)b) PASSED")
    print("TEST 1)b PASSED")


#Test C Duplicated Requests:
def testC():
    
    p = subprocess.Popen (["python", "testserver.py","-d","3","-p","56751"])
    p2 = subprocess.Popen(["python", "server.py","-p","56752"])
    p3 = subprocess.Popen(["python", "server.py","-p","56753"])
    open("./filestore/56751/file_1.txt", 'w').close()
    time.sleep(1)
    def client1_behaviour():
        client= LockClient(interceptor=RetryInterceptor())
        client.RPC_init()
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "A")
        client.RPC_lock_release()
        time.sleep(1)
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "A")
        client.RPC_lock_release()
    def client2_behaviour():
        client= LockClient(interceptor=RetryInterceptor())
        time.sleep(0.1)
        client.RPC_init()
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "B")
        time.sleep(1)
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
    p2.terminate()
    p3.terminate()
    assert open("./filestore/56751/file_1.txt", 'r').read() == "ABBA"
    print("TEST C PASSED")


#Test D Combined network failures:
def testD():
    p = subprocess.Popen (["python", "testserver.py","-d","4","-p","56751"])
    p2 = subprocess.Popen(["python", "server.py","-p","56752"])
    p3 = subprocess.Popen(["python", "server.py","-p","56753"])
    open("./filestore/56751/file_1.txt", 'w').close()
    time.sleep(1)
    def client1_behaviour():
        client= LockClient(interceptor=RetryInterceptor())
        client.RPC_init()
        print(f"Client 1: {client.client_id}")
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "1")
        client.RPC_append_file("file_1.txt", "A")
        client.RPC_lock_release()
        
    def client2_behaviour():
        client= LockClient(interceptor=RetryInterceptor())
        time.sleep(0.1)
        client.RPC_init()
        print(f"Client 2: {client.client_id}")
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
    p2.terminate()
    p3.terminate()
    assert open("./filestore/56751/file_1.txt", 'r').read() == "1AB"
    print("TEST D PASSED")


# Part 2: Client Fails/Stucks
def test2a():
    p = subprocess.Popen (["python", "testserver.py","-p","56751"])
    p2 = subprocess.Popen(["python", "server.py","-p","56752"])
    p3 = subprocess.Popen(["python", "server.py","-p","56753"])
    open("./filestore/56751/file_1.txt", 'w').close()
    time.sleep(1)
    def client1_behaviour():
        client= LockClient(interceptor=RetryInterceptor())
        client.RPC_init()
        client.RPC_lock_acquire()
        time.sleep(8.5)
        status = client.RPC_append_file("file_1.txt", "A",test=True)
        assert status ==lock_pb2.Status.LOCK_EXPIRED  
        print("-------------STATUS CODE CORRECT------------") 
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "A")
        client.RPC_append_file("file_1.txt", "A")
        client.RPC_lock_release()

        
    def client2_behaviour():
        client= LockClient(interceptor=RetryInterceptor())
        time.sleep(0.1)
        client.RPC_init()
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "B")
        time.sleep(1)
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
    p2.terminate()
    p3.terminate()
    assert open("./filestore/56751/file_1.txt", 'r').read() == "BBAA"
    print("TEST 2a PASSED")


# Part 2b: Stucks after editing the file
def test2b():
    p = subprocess.Popen (["python", "testserver.py","-p","56751"])
    p2 = subprocess.Popen(["python", "server.py","-p","56752"])
    p3 = subprocess.Popen(["python", "server.py","-p","56753"])
    open("./filestore/56751/file_1.txt", 'w').close()
    time.sleep(1)
    def client1_behaviour():
        client= LockClient(interceptor=RetryInterceptor())
        client.RPC_init()
        client.RPC_lock_acquire()
        
        client.RPC_append_file("file_1.txt", "A")
        time.sleep(8.1)
        client.RPC_append_file("file_1.txt", "A")
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "A")
        client.RPC_append_file("file_1.txt", "A")
        client.RPC_lock_release()

        
    def client2_behaviour():
        client= LockClient(interceptor=RetryInterceptor())
        # Small pause to make sure this is initialised as client 2
        time.sleep(0.1)
        client.RPC_init()
        # Small pause to ensure client 1 gets the lock first, as described in test 2b
        time.sleep(0.1)
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "B")
        time.sleep(1)
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
    p2.terminate()
    p3.terminate()
    assert open("./filestore/56751/file_1.txt", 'r').read() == "BBAA"
    print("TEST 2b PASSED")

# test 3)a) single server fail, lock is free
def test3a():
    time.sleep(1)
    p = subprocess.Popen (["python", "server.py","-p","56751"])
    time.sleep(1)
    print("hello")
    client= LockClient(interceptor=RetryInterceptor())
    client.RPC_init()
    client.RPC_lock_acquire()
    client.RPC_append_file("file_1.txt", "A")
    client.RPC_append_file("file_1.txt", "A")
    client.RPC_lock_release()
    time.sleep(1)
    p.terminate()
    # Server files now automatically wiped when server is killed
    p = subprocess.Popen (["python", "server.py","-p","56751","-l","1"])
    time.sleep(1)
    client.RPC_lock_acquire()
    client.RPC_append_file("file_1.txt", "1")
    client.RPC_lock_release()
    p.terminate()   
    
    assert open("./filestore/56751/file_1.txt", 'r').read() == "AA1"
    print("TEST 3a PASSED")

def test3b():
    time.sleep(1)
    global p
    p = subprocess.Popen (["python", "server.py","-p","56751"])
    time.sleep(1)
    print("hello")
    
    def client1_behaviour():
        client= LockClient(interceptor=RetryInterceptor())
        client.RPC_init()
        print(f"Client 1 has been given the client ID: {client.client_id}")
        client.RPC_lock_acquire()
        # Allow time for client 2 to ask for the lock
        time.sleep(0.5)
        client.RPC_append_file("file_1.txt", "A")
        client.RPC_lock_release()
        # Sleep to allow client 2 to ask for the lock
        time.sleep(0.2)
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "A")
        client.RPC_lock_release()
        

        
    def client2_behaviour():
        global p
        client= LockClient(interceptor=RetryInterceptor())
        # Small pause to make sure this is initialised as client 2
        time.sleep(0.1)
        client.RPC_init()
        print(f"Client 2 has been given the client ID: {client.client_id}")
        # Small pause to ensure client 1 gets the lock first, as described in test 2b
        time.sleep(0.1)
        client.RPC_lock_acquire()
        
        client.RPC_append_file("file_1.txt", "B")
        # Allow time for log to be updated before crashing
        time.sleep(0.1)
        print(f"SERVER ABOUT TO DIE_________________________________________")
        p.terminate()
        # Server txt files now automatically wiped when server is killed
        p = subprocess.Popen (["python", "server.py","-p","56751","-l","1"])
        # Allow time for server to restart
        time.sleep(1)
        print(f"SERVER HAS COME BACK TO LIFE _____________________________")
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
    
    assert open("./filestore/56751/file_1.txt", 'r').read() == "ABBA"
    print("TEST 3b PASSED")

def test4a():
    global p
    global p2
    global p3
    p = subprocess.Popen (["python", "testserver.py","-p","56751"])
    p2 = subprocess.Popen(["python", "server.py","-p","56752"])
    p3 = subprocess.Popen(["python", "server.py","-p","56753"])
    # Allow time for servers to start
    time.sleep(1)
    print(f"Servers have started")

    def client1_behaviour():
        global p
        global p2
        global p3
        client= LockClient(interceptor=RetryInterceptor())

    def client2_behaviour():
        global p
        global p2
        global p3
        client= LockClient(interceptor=RetryInterceptor())
        # Small pause to make sure this is initialised as client 2
        time.sleep(0.1)
        client.RPC_init()


    thread1 = threading.Thread(target=client1_behaviour)
    thread2 = threading.Thread(target=client2_behaviour)

    # Start the threads
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()
    p.terminate()
    p2.terminate()
    p3.terminate()


    content_56751_file1 = open("./filestore/56751/file_1.txt", 'r').read()
    assert content_56751_file1 == "AB" or content_56751_file1 == "BA"

    content_56751_file2 = open("./filestore/56751/file_2.txt", 'r').read()
    assert content_56751_file2 == "AB" or content_56751_file2 == "BA"

    content_56751_file3 = open("./filestore/56751/file_3.txt", 'r').read()
    assert content_56751_file3 == "AB" or content_56751_file3 == "BA"

    content_56752_file1 = open("./filestore/56752/file_1.txt", 'r').read()
    assert content_56752_file1 == "AB" or content_56752_file1 == "BA"

    content_56752_file2 = open("./filestore/56752/file_2.txt", 'r').read()
    assert content_56752_file2 == "AB" or content_56752_file2 == "BA"

    content_56752_file3 = open("./filestore/56752/file_3.txt", 'r').read()
    assert content_56752_file3 == "AB" or content_56752_file3 == "BA"

    content_56753_file1 = open("./filestore/56753/file_1.txt", 'r').read()
    assert content_56753_file1 == "AB" or content_56753_file1 == "BA"

    content_56753_file2 = open("./filestore/56753/file_2.txt", 'r').read()
    assert content_56753_file2 == "AB" or content_56753_file2 == "BA"

    content_56753_file3 = open("./filestore/56753/file_3.txt", 'r').read()
    assert content_56753_file3 == "AB" or content_56753_file3 == "BA"

    print("TEST 4a PASSED")







# testA()
# testB()
# testC()
# testD()
# test2a()
# test2b()
# test3a()
test3b()
