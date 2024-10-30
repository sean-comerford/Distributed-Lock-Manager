import grpc
import lock_pb2
import lock_pb2_grpc

class LockClient:
    def __init__(self):
        self.channel = grpc.insecure_channel('localhost:56751')
        self.stub = lock_pb2_grpc.LockServiceStub(self.channel)
        self.client_id = None

    def RPC_init(self):
        request = lock_pb2.Int()
        response = self.stub.client_init(request)
        self.client_id = response.rc
        print(f"Successfully connected to server with client ID: {self.client_id}")
            
    def RPC_lock_acquire(self):
        request = lock_pb2.lock_args(client_id=self.client_id)
        response = self.stub.lock_acquire(request)
        print(f"Lock acquired")

    def RPC_lock_release(self):
        request = lock_pb2.lock_args(client_id=self.client_id)
        response = self.stub.lock_release(request)
        print(f"Lock released")

    def RPC_append_file(self, file):
        request = lock_pb2.file_args(filename = file , content = bytes("TEST", 'utf-8'), client_id=self.client_id) #For test purposes
        response = self.stub.file_append(request)
        print(f"File appended/failed") #Error handling for different responses (goes for all rpc calls)

    def RPC_close(self):
        request = lock_pb2.Int(rc=self.client_id)
        response = self.stub.client_close(request)
        print("Client connection closed.")

if __name__ == "__main__":
    client = LockClient()
    client.RPC_init()
    client.RPC_lock_acquire()
    client.RPC_append_file(file= "file_1.txt")
    
