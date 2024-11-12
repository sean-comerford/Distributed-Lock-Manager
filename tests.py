from io import StringIO
import sys
from middleware import RetryInterceptor
from client_library import LockClient
import time
import subprocess
import threading
import os
import signal




# Test 1 Packet Delay

def test1():
    p = subprocess.Popen(["python", "server.py",])
    time.sleep(1)
    client= LockClient(interceptor=RetryInterceptor())
    client2 = LockClient(interceptor=RetryInterceptor())
    capturedOutput = StringIO()         # Make StringIO.
    sys.stdout = capturedOutput                  # Redirect stdout.
    client.RPC_init()
    client2.RPC_init()
    client.RPC_lock_acquire()
    client2.RPC_lock_acquire()
    time.sleep(3)
    client.RPC_append_file("A.txt", "Hello")                                # Call function.
    sys.stdout = sys.__stdout__                  # Reset redirect.
    print('Captured', capturedOutput.getvalue())  # Now works.
    print(capturedOutput.getvalue()[-100:])
    p.terminate()
# test1()

# Test 2: Packet Drop
def test2():
    p = subprocess.Popen (["python", "server.py","-d"])
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
test2()
