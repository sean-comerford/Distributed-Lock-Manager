import grpc
import lock_pb2
import lock_pb2_grpc
import argparse
import json
from middleware import RetryInterceptor
import time

ports = [
            'localhost:56751',
            'localhost:56752',
            'localhost:56753'
]

class LockClient:
    def __init__(self, interceptor=None):
        # Create channel with or without the interceptor
        self.leader = self.RPC_get_leader()
        if interceptor:
            self.interceptor=interceptor
            interceptor.client = self
            self.channel = grpc.intercept_channel(grpc.insecure_channel(self.leader),interceptor)
        else:
            self.channel = grpc.insecure_channel(self.leader)

        # Create stub
        self.stub = lock_pb2_grpc.LockServiceStub(self.channel)
        self.client_id = None
        self.lock_val = None
    
    def retries(self, max_retries,place,query):
        """
        description: retries a function call up to max_retries times
        input: max_retries, place, query
        output: response    
        """
        retries = 0
        while retries < max_retries:
            try:
                response = place(query)
                return response
            except grpc.RpcError as rpc_error:
                print(f"Client{self.client_id}:Call failed with code: {rpc_error.code()}")
                retries += 1
        return False

    def RPC_init(self):
        request = lock_pb2.Int()
        # response = self.retries(max_retries=5,place=self.stub.client_init,query=request)
        response=self.channel_check('client_init',request)
        self.client_id = response.id_num
        print(f"Client{self.client_id}:Successfully connected to server with client ID: {self.client_id}")
            
    def RPC_lock_acquire(self):
        if self.lock_val == None:
            request = lock_pb2.lock_args(client_id=self.client_id)
            print(f"Client{self.client_id}:Waiting for lock...")
            response = self.stub.lock_acquire(request)
            if response.status == lock_pb2.Status.SUCCESS:
                print(f"Client{self.client_id}:Lock acquired")
                self.lock_val = response.id_num
        else:
            print(f"Client{self.client_id}:LOCK ALREADY OWNED")

    def RPC_lock_release(self):
        print(f"Client{self.client_id}: Attempting to release lock with client ID: {self.client_id}")
        request = lock_pb2.lock_args(client_id=self.client_id,lock_val=self.lock_val)
        response = self.stub.lock_release(request)
        if response.status == lock_pb2.Status.SUCCESS:
            print(f"Client{self.client_id}:Lock released")
        else:
            print(f"Client{self.client_id}:DID NOT OWN LOCK - reset lock_val")
        self.lock_val = None

    def RPC_append_file(self, file, content,test=False):
        if(self.lock_val is not None):
            request = lock_pb2.file_args(filename = file , content = bytes(content, 'utf-8'), client_id=self.client_id,lock_val=self.lock_val) # Specify content to append
            response = self.stub.file_append(request)
            if response.status == lock_pb2.Status.LOCK_NOT_ACQUIRED:
                print(f"Client{self.client_id}: DID NOT OWN LOCK - reset lock_val")
                self.lock_val = None
            if test:
                return response.status
        else:
            print(f"Client{self.client_id}:  ERROR: LOCK_EXPIRED")

    def RPC_get_leader(self):
        for server in ports:
            try:
                self.channel = grpc.insecure_channel(server)
                self.stub = lock_pb2_grpc.LockServiceStub(self.channel)
                response = self.stub.get_leader(lock_pb2.Int())
                if response.status == lock_pb2.Status.SUCCESS:
                    leader_server = response.server
                    print(f"Leader discovered at {leader_server}")
                    return leader_server
            except grpc.RpcError:
                continue
        raise Exception("Failed to discover leader.")

    def RPC_close(self):
        request = lock_pb2.Int(rc=self.client_id)
        response = self.stub.client_close(request)
        # Explicitly closing the gRPC channel.
        self.channel.close()
        print(f"Client{self.client_id}:Client connection closed.")
        
    def channel_check(self,method_name,request):
        try:
            response = getattr(self.stub, method_name)(request)
            return response
        except grpc._channel._InactiveRpcError as e:
            self.leader = self.RPC_get_leader()
            self.channel = grpc.intercept_channel(grpc.insecure_channel(self.leader),self.interceptor)

# Interactive command loop for testing and debugging
def command_loop(client):
    print("Entering interactive mode. Type 'help' for a list of commands. Type 'exit' to quit.")
    while True:
        cmd = input("Enter command: ").strip().lower()
        if cmd == "init":
            client.RPC_init()
        elif cmd == "acquire":
            client.RPC_lock_acquire()
        elif cmd == "append":
            filename = input("Enter filename: ").strip()
            content = input("Enter content: ").strip()
            client.RPC_append_file(filename, content)
        elif cmd == "release":
            client.RPC_lock_release()
        elif cmd == "close":
            client.RPC_close()
            break  # Exit loop after closing
        elif cmd == "help":
            print("Available commands:")
            print("init     : Initialize the client and get client ID")
            print("acquire  : Acquire the lock")
            print("append      : Append to a file")
            print("release  : Release the lock")
            print("close    : Close the client connection and exit")
        elif cmd == "exit":
            print("Exiting interactive mode.")
            break
        else:
            print(f"Unknown command: {cmd}. Type '--help' for a list of commands.")


if __name__ == "__main__":
    # Argument to start in interactive mode
    parser = argparse.ArgumentParser(description="LockClient operations")
    parser.add_argument("-i", "--interactive", action="store_true", help="Enter interactive mode")
    args = parser.parse_args()

    # Initialize client and enter command loop if interactive mode is selected
    client = LockClient(interceptor=RetryInterceptor())
    if args.interactive:
        command_loop(client)
