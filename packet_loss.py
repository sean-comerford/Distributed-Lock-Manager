from client_library import LockClient 
import grpc
import random
import threading
import time
import logging

# cases to think about:
# 1. request doesnt reach server
# 2. delayed request hits server

class PacketLossInterceptor(grpc.UnaryUnaryClientInterceptor):
    def __init__(self, drop_probability=0.5):
        self.drop_probability = drop_probability

    def intercept_unary_unary(self, continuation, client_call_details, request):
        # Randomly decide whether to drop this request
        
            
        return continuation(client_call_details, request)

client = LockClient(interceptor=None)
logging.basicConfig(level=logging.INFO)
logging.basicConfig()
client.RPC_init()
client.RPC_close()
#client.RPC_lock_acquire()

#client.RPC_lock_release()

#client.RPC_close()

