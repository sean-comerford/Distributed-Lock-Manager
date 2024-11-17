from server import LockService
import argparse
import grpc
from concurrent import futures
import time
import threading
import lock_pb2
import lock_pb2_grpc

timeout = 100
port = '127.0.0.1:56751'


class LockServiceWrapper:
    def get_request_id(self, context):
        '''Helper method to get request ID from client'''
        for key, value in context.invocation_metadata():
            if key == "request-id":
                return value
        
    def __init__(self, drop=False,port=56751):
        # Initialize the actual LockService instance with the provided arguments
        self.drop = drop
        self.testing_counter =0
        self._lock_service = LockService(port="127.0.0.1:"+str(port))
    
    def client_init(self, request, context):
        print(f"Wrapper: client_init called by client {request.client_id}")
        return self._lock_service.client_init(request, context)

    def client_close(self, request, context):
        print("Wrapper: client_close called")
        return self._lock_service.client_close(request, context)

    def lock_acquire(self, request, context):
        print(f"Wrapper: lock_acquire called by client {request.client_id}")
        if self.drop == 1:
                self.drop = False
                print(f"\n\n\nSIMULATED ARRIVAL PACKET LOSS for Client {request.client_id}.")
                time.sleep(12.1)
        response = self._lock_service.lock_acquire(request, context)
        if self.drop == 2:
                print(f"\n\n\nSIMULATED RETURN PACKET LOSS {request.client_id}.")
                self.drop = False
                time.sleep(12)
        return response

    def lock_release(self, request, context):
        print("Wrapper: lock_release called")
        if self.drop == 3:
                print(f"\n\n\nSIMULATED PACKET DELAY {request.client_id}.")
                self.drop = False
                time.sleep(1)
        return self._lock_service.lock_release(request, context)

    def sendBytes(self, request, context):
        print("Wrapper: sendBytes called")
        return self._lock_service.sendBytes(request, context)

    def file_append(self, request, context):
        request_id = self.get_request_id(context)
        print(f"Wrapper: file_append called by client {request.client_id} to append {request.content} with request_id {request_id}")
        if self.drop == 5:
                    time.sleep(8.1)
                    self.drop = False
        self.testing_counter += 1
        if (self.drop == 4 and self.testing_counter==2):
                print(f"\n\n\nSIMULATED PACKET ARRIVAL LOST. Append {request.content} for client {request.client_id}.")
                # self.drop = False
                time.sleep(12.1)
        response = self._lock_service.file_append(request, context)
        if (self.drop == 4 and self.testing_counter==3):
                print(f"\n\n\nSIMULATED PACKET RESPONSE LOST {request.client_id}. Response is ")
                self.drop = False
                time.sleep(12.1)
        return response
    

    def request_vote(self, request, context):
        print("Wrapper: request_vote called")
        return self._lock_service.request_vote(request, context)

    def heartbeat(self, request, context):
        print("Wrapper: heartbeat called")
        return self._lock_service.heartbeat(request, context)

    def get_leader(self, request, context):
        print(f"Wrapper: get_leader called by client {request.client_id}")
        return self._lock_service.get_leader(request, context)      
    

    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LockClient operations")
    parser.add_argument(
        "-d", "--drop",
        type=int,
        choices=[1, 2, 3, 4, 5],  # Limit acceptable values
        help="Drop packet on lock acquire: 1=lost on the way there, 2=lost on the way back"
    )
    parser.add_argument(
        "-p", "--port",
    )
    args = parser.parse_args()
    if args.port:
        port1=args.port
    else:
        port1=str(56751)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=100))
    if args.drop:
        lock_pb2_grpc.add_LockServiceServicer_to_server(LockServiceWrapper(drop=args.drop,port=port1), server)
    else:
        lock_pb2_grpc.add_LockServiceServicer_to_server(LockServiceWrapper(drop=False,port=port1), server)
    server.add_insecure_port(port)
    server.start()
    print("Server started (localhost) on port 56751.")
    server.wait_for_termination()
