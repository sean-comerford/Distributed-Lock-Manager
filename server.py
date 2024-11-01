import grpc
from concurrent import futures
import time
import threading
import lock_pb2
import lock_pb2_grpc

timeout = 100
port = '127.0.0.1:56751'

class LockService(lock_pb2_grpc.LockServiceServicer):

    def __init__(self):
        self.locked = False #Is Lock locked?
        self.lock = threading.Lock() #Mutual Exclusion on shared resources (self.locked, client_counter and lock_owner)
        self.condition = threading.Condition(self.lock) #Coordinate access to the lock by allowing threads (clients) to wait until lock availabel
        self.client_counter = 0
        self.lock_owner = None
        self.files = {f'file_{i}.txt': [] for i in range(100)} #Change to however we want out files to look

    def client_init(self, request, context):
        with self.lock:
            self.client_counter += 1
            client_id = self.client_counter
        print(f"Client initialized with ID {client_id}")
        return lock_pb2.Int(rc=client_id)
    
    def client_close(self, request, context):
        with self.lock:
            if self.lock_owner == request.rc:
                self.locked = False
                self.condition.notify_all()
                self.lock_owner = None
                print(f"Lock released due to client {request.rc} closing.")

            print(f"Client {request.rc} closed") #How else to close?
            return lock_pb2.Response(status=lock_pb2.Status.SUCCESS)
    
    def lock_acquire(self, request, context):
        with self.condition:
            while self.locked:
                print(f"Client {request.client_id} waiting for lock.")
                self.condition.wait()
            self.locked = True
            self.lock_owner = request.client_id
            print(f"Lock granted to client {request.client_id}")
            return lock_pb2.Response(status=lock_pb2.Status.SUCCESS)
        
    def lock_release(self, request, context):
        with self.condition:
            if self.locked and self.lock_owner == request.client_id:
                self.locked = False
                self.lock_owner = None
                print(f"Lock released by client {request.client_id}")
                self.condition.notify_all()
                return lock_pb2.Response(status=lock_pb2.Status.SUCCESS)
            elif not self.locked:
                print(f"Client {request.client_id} attempted to release a lock that was not acquired.")
                return lock_pb2.Response(status=lock_pb2.Status.FILE_ERROR) #Not a file error but all we have in proto?
            else:
                print(f"Client {request.client_id} attempted to release a lock owned by client {self.lock_owner}.")
                return lock_pb2.Response(status=lock_pb2.Status.FILE_ERROR) #Again Not file error
    
    def file_append(self, request, context):
        if self.lock_owner != request.client_id:
            print(f"Client {request.client_id} does not have access to lock")
            return lock_pb2.Response(status=lock_pb2.Status.FILE_ERROR)
        if request.filename not in self.files:
            print(f"Filename {request.filename} does not exist")
            return lock_pb2.Response(status=lock_pb2.Status.FILE_ERROR)
        print(f"Client {request.client_id} appended to file {request.filename}")
        with open(request.filename, 'ab') as file:
            file.write(request.content)
        return lock_pb2.Response(status=lock_pb2.Status.SUCCESS)
    
if __name__ == "__main__":
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=100))
    lock_pb2_grpc.add_LockServiceServicer_to_server(LockService(), server)
    server.add_insecure_port(port)
    server.start()
    print("Server started (localhost) on port 56751.")
    server.wait_for_termination()
