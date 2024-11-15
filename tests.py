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
    open("file_1.txt", 'w').close()
    p = subprocess.Popen(["python", "testserver.py","-d","5"])
    time.sleep(1)
    def client1_behaviour():
        client= LockClient(interceptor=RetryInterceptor())
        client.RPC_init()
        client.RPC_lock_acquire()
        status = client.RPC_append_file("file_1.txt", "A",test=True)  
        assert status ==lock_pb2.Status.LOCK_EXPIRED
        print("-------------STATUS CODE CORRECT------------")
    def client2_behaviour():
        client2 = LockClient(interceptor=RetryInterceptor())             
        client2.RPC_init()
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
    assert open("file_1.txt", 'r').read() == ""
   
    
    print("TEST 1 PASSED")


# Test B: Packet Drop
def testB():
    open("file_1.txt", 'w').close()
    p = subprocess.Popen (["python", "testserver.py","-d","1"])
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
    assert open("file_1.txt", 'r').read() == "BA"


    # part b
    print("TEST b)a) PASSED")
    open("file_1.txt", 'w').close()
    p = subprocess.Popen (["python", "testserver.py","-d","2"])
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
    assert open("file_1.txt", 'r').read() == "AB"
    print("TEST 1)b)b) PASSED")
    print("TEST 1)b PASSED")


#Test C Duplicated Requests:
def testC():
    open("file_1.txt", 'w').close()
    p = subprocess.Popen (["python", "testserver.py","-d","3"])
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
    assert open("file_1.txt", 'r').read() == "ABBA"
    print("TEST C PASSED")


#Test D Combined network failures:
def testD():
    open("file_1.txt", 'w').close()
    p = subprocess.Popen (["python", "testserver.py","-d","4"])
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
    assert open("file_1.txt", 'r').read() == "1AB"
    print("TEST D PASSED")


# Part 2: Client Fails/Stucks
def test2a():
    open("file_1.txt", 'w').close()
    p = subprocess.Popen (["python", "testserver.py"])
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
    assert open("file_1.txt", 'r').read() == "BBAA"
    print("TEST 2a PASSED")


# Part 2b: Stucks after editing the file
def test2b():
    open("file_1.txt", 'w').close()
    p = subprocess.Popen (["python", "testserver.py"])
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
    assert open("file_1.txt", 'r').read() == "BBAA"
    print("TEST 2b PASSED")

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



#testA()
#testB()
#testC()
testD()
#test2a()
#test2b()
#testLog()
#testLog2()
