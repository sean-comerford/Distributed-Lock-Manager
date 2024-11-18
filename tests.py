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
import json
import glob


def clear_json_files():
    # List of file paths to clear
    file_paths = [
        "./filestore/56751/56751.json",
        "./filestore/56752/56752.json",
        "./filestore/56753/56753.json"
    ]
    
    # Iterate over the file paths
    for file_path in file_paths:
        # Check if the file exists
        if os.path.exists(file_path):
            try:
                # Write an empty JSON object to the file
                with open(file_path, "w") as file:
                    json.dump({}, file)
                print(f"Cleared: {file_path}")
            except Exception as e:
                print(f"Error clearing {file_path}: {e}")
        else:
            print(f"File not found: {file_path}")
    directories = ["./filestore/56751", "./filestore/56752", "./filestore/56753"]

    # Iterate over the directories
    for directory in directories:
        # Use glob to find all .txt files in the directory
        txt_files = glob.glob(os.path.join(directory, "*.txt"))
        for txt_file in txt_files:
            try:
                os.remove(txt_file)  # Delete the .txt file
                print(f"Deleted: {txt_file}")
            except Exception as e:
                print(f"Error deleting {txt_file}: {e}")
# Test A Packet Delay

def testA():
    clear_json_files()
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
    clear_json_files()
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
    clear_json_files()
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
    clear_json_files()
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
    clear_json_files()
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
    clear_json_files()
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
    clear_json_files()
    # For testing purposes, make sure the file is empty
    open("./filestore/56751/file_1.txt", 'w').close()
    time.sleep(1)
    p = subprocess.Popen (["python", "server.py","-p","56751"])
    p2 = subprocess.Popen(["python", "server.py","-p","56752"])
    p3 = subprocess.Popen(["python", "server.py","-p","56753"])
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
    #p = subprocess.Popen (["python", "server.py","-p","56751","-l","1"])
    p = subprocess.Popen (["python", "server.py","-p","56751"])
    time.sleep(1)
    client.RPC_lock_acquire()
    client.RPC_append_file("file_1.txt", "1")
    client.RPC_lock_release()
    p.terminate() 
    p2.terminate()
    p3.terminate()  
    
    assert open("./filestore/56751/file_1.txt", 'r').read() == "AA1"
    print("TEST 3a PASSED")

def test3b():
    clear_json_files()
    # For testing purposes, make sure the file is empty
    open("./filestore/56751/file_1.txt", 'w').close()
    time.sleep(1)
    global p
    p = subprocess.Popen (["python", "server.py","-p","56751"])
    p2 = subprocess.Popen(["python", "server.py","-p","56752"])
    p3 = subprocess.Popen(["python", "server.py","-p","56753"])
    time.sleep(2)
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
        global p2
        global p3
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
    p2.terminate()
    p3.terminate()
    
    assert open("./filestore/56751/file_1.txt", 'r').read() == "ABBA"
    print("TEST 3b PASSED")


def test4a():
    global p
    global p2
    global p3
    clear_json_files()
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
        client.RPC_init()
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "A")
        client.RPC_append_file("file_2.txt", "A")
        p2.terminate()
        p2 = subprocess.Popen(["python", "server.py","-p","56752"])
        print("server 2 restarted")
        time.sleep(1)
        client.RPC_append_file("file_3.txt", "A")
        client.RPC_lock_release()

    def client2_behaviour():
        global p
        global p2
        global p3
        client= LockClient(interceptor=RetryInterceptor())
        # Small pause to make sure this is initialised as client 2
        time.sleep(0.1)
        client.RPC_init()
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "B")
        client.RPC_append_file("file_2.txt", "B")
        client.RPC_append_file("file_3.txt", "B")
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


    content_56751_file1 = open("./filestore/56751/file_1.txt", 'r').read()
    assert content_56751_file1 == "AB" or content_56751_file1 == "BA"

    content_56751_file2 = open("./filestore/56751/file_2.txt", 'r').read()
    assert content_56751_file2 == content_56751_file1

    content_56751_file3 = open("./filestore/56751/file_3.txt", 'r').read()
    assert content_56751_file3 == content_56751_file1

    content_56752_file1 = open("./filestore/56752/file_1.txt", 'r').read()
    assert content_56752_file1 == content_56751_file1

    content_56752_file2 = open("./filestore/56752/file_2.txt", 'r').read()
    assert content_56752_file2 == content_56751_file1

    content_56752_file3 = open("./filestore/56752/file_3.txt", 'r').read()
    assert content_56752_file3 ==  content_56751_file1

    content_56753_file1 = open("./filestore/56753/file_1.txt", 'r').read()
    assert content_56753_file1 == "AB" or content_56751_file1

    content_56753_file2 = open("./filestore/56753/file_2.txt", 'r').read()
    assert content_56753_file2 ==  content_56751_file1

    content_56753_file3 = open("./filestore/56753/file_3.txt", 'r').read()
    assert content_56753_file3 ==  content_56751_file1

    print("TEST 4a PASSED")


def test4c():
    global p
    global p2
    global p3
    clear_json_files()
    p = subprocess.Popen (["python", "testserver.py","-p","56751"])
    p2 = subprocess.Popen(["python", "server.py","-p","56752"])
    p3 = subprocess.Popen(["python", "server.py","-p","56753"])
    # Allow time for servers to start
    time.sleep(4)
    print(f"Servers have started")       

    def client1_behaviour():
        global p
        global p2
        global p3
        client= LockClient(interceptor=RetryInterceptor())
        client.RPC_init()
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "A")
        client.RPC_append_file("file_1.txt", "A")
        client.RPC_append_file("file_1.txt", "A")
        client.RPC_append_file("file_1.txt", "A")
        client.RPC_append_file("file_1.txt", "A") 
        print(f"---------------------LOCK RELEASE ABOUT TO BE CALLED BY CLIENT 1---------------------")
        client.RPC_lock_release()

    def client2_behaviour():
        global p
        global p2
        global p3
        client= LockClient(interceptor=RetryInterceptor())
        # Small pause to make sure server client1 releases
        time.sleep(1)
        client.RPC_init()
        print(f"---------------------LEADER SERVER ABOUT TO CRASH---------------------")
        p.terminate()
        
        time.sleep(4)
        
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "B")
        client.RPC_append_file("file_1.txt", "B")
        client.RPC_append_file("file_1.txt", "B")
        client.RPC_append_file("file_1.txt", "B")
        client.RPC_append_file("file_1.txt", "B")
        client.RPC_lock_release()


    def client3_behaviour():
        global p
        global p2
        global p3
        client= LockClient(interceptor=RetryInterceptor())
        # Small pause to make sure this is initialised as client 3 anjd server crashes
        time.sleep(2)
        client.RPC_init()
        time.sleep(6)
        
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "C")
        client.RPC_append_file("file_1.txt", "C")
        client.RPC_append_file("file_1.txt", "C")
        client.RPC_append_file("file_1.txt", "C")
        client.RPC_append_file("file_1.txt", "C")
        client.RPC_lock_release()
        p = subprocess.Popen(["python", "testserver.py","-p","56751","-x","1"])
        time.sleep(6)
        
    thread1 = threading.Thread(target=client1_behaviour)
    thread2 = threading.Thread(target=client2_behaviour)
    thread3 = threading.Thread(target=client3_behaviour)

    # Start the threads
    thread1.start()
    thread2.start()
    thread3.start()
    thread1.join()
    thread2.join()
    thread3.join()
    p.terminate()
    p2.terminate()
    p3.terminate()
    content_56751_file1 = open("./filestore/56751/file_1.txt", 'r').read()
    assert content_56751_file1 == "AAAAABBBBBCCCCC" or content_56751_file1 == "AAAAACCCCCBBBBB"

    content_56752_file1 = open("./filestore/56752/file_1.txt", 'r').read()
    assert content_56752_file1 == "AAAAABBBBBCCCCC" or content_56752_file1 == "AAAAACCCCCBBBBB"

    content_56753_file1 = open("./filestore/56753/file_1.txt", 'r').read()
    assert content_56753_file1 == "AAAAABBBBBCCCCC" or content_56753_file1 == "AAAAACCCCCBBBBB"
    
    assert content_56751_file1==content_56752_file1 and content_56751_file1==content_56753_file1

    print(f"Test 4c has PASSED")
    
def test4d():
    global p
    global p2
    global p3
    clear_json_files()
    p = subprocess.Popen (["python", "testserver.py","-p","56751"])
    p2 = subprocess.Popen(["python", "server.py","-p","56752"])
    p3 = subprocess.Popen(["python", "server.py","-p","56753"])
    # Allow time for servers to start
    time.sleep(4)
    print(f"Servers have started")       

    def client1_behaviour():
        global p
        global p2
        global p3
        client= LockClient(interceptor=RetryInterceptor())
        client.RPC_init()
        client.RPC_lock_acquire()
        for i in range(20):
            client.RPC_append_file("file_1.txt", "A")
        print(f"---------------------LOCK RELEASE ABOUT TO BE CALLED BY CLIENT 1---------------------")
        client.RPC_lock_release()

    def client2_behaviour():
        global p
        global p2
        global p3
        client= LockClient(interceptor=RetryInterceptor())
        # Small pause to make sure server client1 releases
        time.sleep(2)
        client.RPC_init()
        client.RPC_lock_acquire()
        for i in range(10):
            client.RPC_append_file("file_1.txt", "B")
        print(f"---------------------LEADER SERVER ABOUT TO CRASH---------------------")
        p.terminate()
        #time.sleep(3)
        client.RPC_init()
        client.RPC_lock_acquire()
        print("--------------------20 Bs")
        for i in range(20):
            client.RPC_append_file("file_1.txt", "B")
        print(f"---------------------LOCK RELEASE ABOUT TO BE CALLED BY CLIENT 2---------------------")
        client.RPC_lock_release()
        


    def client3_behaviour():
        global p
        global p2
        global p3
        client= LockClient(interceptor=RetryInterceptor())
        # Small pause to make sure this is initialised as client 3 anjd server crashes
        time.sleep(10)
        client.RPC_init()
        client.RPC_lock_acquire()
        for i in range(20):
            client.RPC_append_file("file_1.txt", "C")
        client.RPC_lock_release()
        p = subprocess.Popen(["python", "testserver.py","-p","56751","-x","1"])
        time.sleep(3)
        
    thread1 = threading.Thread(target=client1_behaviour)
    thread2 = threading.Thread(target=client2_behaviour)
    thread3 = threading.Thread(target=client3_behaviour)

    # Start the threads
    thread1.start()
    thread2.start()
    thread3.start()
    thread1.join()
    thread2.join()
    thread3.join()
    p.terminate()
    p2.terminate()
    p3.terminate()
    content_56751_file1 = open("./filestore/56751/file_1.txt", 'r').read()
    assert content_56751_file1 == "AAAAAAAAAAAAAAAAAAAABBBBBBBBBBBBBBBBBBBBCCCCCCCCCCCCCCCCCCCC"

    content_56752_file1 = open("./filestore/56752/file_1.txt", 'r').read()
    assert content_56752_file1 == "AAAAAAAAAAAAAAAAAAAABBBBBBBBBBBBBBBBBBBBCCCCCCCCCCCCCCCCCCCC"

    content_56753_file1 = open("./filestore/56753/file_1.txt", 'r').read()
    assert content_56753_file1 == "AAAAAAAAAAAAAAAAAAAABBBBBBBBBBBBBBBBBBBBCCCCCCCCCCCCCCCCCCCC"
    
    print(f"Test 4d has PASSED")
def test4b():
    global p
    global p2
    global p3
    clear_json_files()
    p = subprocess.Popen (["python", "testserver.py","-p","56751"])
    p2 = subprocess.Popen(["python", "server.py","-p","56752"])
    p3 = subprocess.Popen(["python", "server.py","-p","56753"])
    # Allow time for servers to start
    time.sleep(2)
    print(f"Servers have started")

    def client1_behaviour():
        global p
        global p2
        global p3
        client= LockClient(interceptor=RetryInterceptor())
        client.RPC_init()
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "A")
        client.RPC_append_file("file_2.txt", "A")
        print("server down")
        p2.terminate()
        # server dies for 10s
        client.RPC_append_file("file_3.txt", "A")
        client.RPC_lock_release()
        time.sleep(10)
        
        p2 = subprocess.Popen(["python", "server.py","-p","56752"])
        time.sleep(4)
        print("server up")
        

    def client2_behaviour():
        global p
        global p2
        global p3
        client= LockClient(interceptor=RetryInterceptor())
        # Small pause to make sure this is initialised as client 2
        time.sleep(0.1)
        client.RPC_init()
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "B")
        client.RPC_append_file("file_2.txt", "B")
        client.RPC_append_file("file_3.txt", "B")
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


    content_56751_file1 = open("./filestore/56751/file_1.txt", 'r').read()
    assert content_56751_file1 == "AB" or content_56751_file1 == "BA"

    content_56751_file2 = open("./filestore/56751/file_2.txt", 'r').read()
    assert content_56751_file2 == content_56751_file1

    content_56751_file3 = open("./filestore/56751/file_3.txt", 'r').read()
    assert content_56751_file3 == content_56751_file1

    content_56752_file1 = open("./filestore/56752/file_1.txt", 'r').read()
    assert content_56752_file1 == content_56751_file1

    content_56752_file2 = open("./filestore/56752/file_2.txt", 'r').read()
    assert content_56752_file2 == content_56751_file1

    content_56752_file3 = open("./filestore/56752/file_3.txt", 'r').read()
    assert content_56752_file3 ==  content_56751_file1

    content_56753_file1 = open("./filestore/56753/file_1.txt", 'r').read()
    assert content_56753_file1 == "AB" or content_56751_file1

    content_56753_file2 = open("./filestore/56753/file_2.txt", 'r').read()
    assert content_56753_file2 ==  content_56751_file1

    content_56753_file3 = open("./filestore/56753/file_3.txt", 'r').read()
    assert content_56753_file3 ==  content_56751_file1

    print("TEST 4b PASSED")


def test4e():
    global p
    global p2
    global p3
    clear_json_files()
    p = subprocess.Popen (["python", "testserver.py","-p","56751"])
    p2 = subprocess.Popen(["python", "server.py","-p","56752"])
    p3 = subprocess.Popen(["python", "server.py","-p","56753"])
    # Allow time for servers to start
    time.sleep(3)
    print(f"Servers have started")       

    def client1_behaviour():
        global p
        global p2
        global p3
        client= LockClient(interceptor=RetryInterceptor())
        client.RPC_init()
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "A")
        client.RPC_append_file("file_1.txt", "A")
        client.RPC_append_file("file_2.txt", "A")
        client.RPC_append_file("file_2.txt", "A")
        client.RPC_append_file("file_3.txt", "A") 
        p2.terminate()
        client.RPC_append_file("file_3.txt", "A")
        client.RPC_append_file("file_4.txt", "A")
        client.RPC_append_file("file_4.txt", "A")
        client.RPC_append_file("file_5.txt", "A")
        client.RPC_append_file("file_5.txt", "A")
        print(f"---------------------LOCK RELEASE ABOUT TO BE CALLED BY CLIENT 1---------------------")
        client.RPC_lock_release()
        p2 = subprocess.Popen(["python", "server.py","-p","56752"])
        # Allow time for server to restart
        time.sleep(1)

    
    def client2_behaviour():
        global p
        global p2
        global p3
        client= LockClient(interceptor=RetryInterceptor())
        # Small pause to make sure this is initialised as client 2
        time.sleep(0.1)
        client.RPC_init()
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "B")
        client.RPC_append_file("file_1.txt", "B")
        client.RPC_append_file("file_2.txt", "B")
        client.RPC_append_file("file_2.txt", "B")
        client.RPC_append_file("file_3.txt", "B")
        print(f"---------------------TWO SERVERS ABOUT TO CRASH---------------------")
        p2.terminate()
        p3.terminate()
        client.RPC_append_file("file_3.txt", "B")
        client.RPC_append_file("file_4.txt", "B")
        client.RPC_append_file("file_4.txt", "B")
        client.RPC_append_file("file_5.txt", "B")
        client.RPC_append_file("file_5.txt", "B")
        client.RPC_lock_release()


    def client3_behaviour():
        global p
        global p2
        global p3
        client= LockClient(interceptor=RetryInterceptor())
        # Small pause to make sure this is initialised as client 3
        time.sleep(0.2)
        client.RPC_init()
        # Wait to let two servers crash on thread 2
        time.sleep(3)
        # Revive one server
        print(f"---------------------ONE SERVER ABOUT TO REVIVE---------------------")
        p2 = subprocess.Popen(["python", "server.py","-p","56752"])
        # Wait to let the server revive
        time.sleep(1)
        client.RPC_lock_acquire()
        client.RPC_append_file("file_1.txt", "C")
        client.RPC_append_file("file_1.txt", "C")
        client.RPC_append_file("file_2.txt", "C")
        client.RPC_append_file("file_2.txt", "C")
        client.RPC_append_file("file_3.txt", "C")
        client.RPC_append_file("file_3.txt", "C")
        client.RPC_append_file("file_4.txt", "C")
        client.RPC_append_file("file_4.txt", "C")
        client.RPC_append_file("file_5.txt", "C")
        client.RPC_append_file("file_5.txt", "C")
        client.RPC_lock_release()
    
    thread1 = threading.Thread(target=client1_behaviour)
    thread2 = threading.Thread(target=client2_behaviour)
    thread3 = threading.Thread(target=client3_behaviour)

    # Start the threads
    thread1.start()
    thread2.start()
    thread3.start()
    thread1.join()
    thread2.join()
    thread3.join()
    p.terminate()
    p2.terminate()
    p3.terminate()

    print(f"Test 4e has finished")




testA()
testB()
testC()
testD()
test2a()
test2b()
test3a()
test3b()
test4a()
test4b()
test4c()
test4d()
#testA()

