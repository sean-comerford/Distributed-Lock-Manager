import grpc
from concurrent import futures
import time
import threading
import lock_pb2
import lock_pb2_grpc
import random
import asyncio
import logging

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
        # Cache to store the processed requests and their responses
        self.response_cache = {}

    def get_request_id(self, context):
        '''Helper method to get request ID from client'''
        for key, value in context.invocation_metadata():
            if key == "request-id":
                return value
    
    def return_cached_response(self, request_id, context):
        '''Return cached response if available, otherwise return 0'''
        return self.response_cache[request_id]

    def initialise_cache(self, request_id):
        '''Initialise cache with request_id and return 0'''
        self.response_cache[request_id] = 0


    def update_cache(self, request_id, response):
        '''Store response in cache keyed by request_id'''
            # Initialise the cache dict with key = request_id and value = 0
            # This value will be updated when the server finishes processing the request
            # Initalising request with empty value allows the server to recognise a repeated duplicate request
        self.response_cache[request_id] = response


    def print_metadata(self, context):
        '''Helper method to print metadata from client'''
        metadata_str = ", ".join(f"{key}={value}" for key, value in context.invocation_metadata())
        print(f"Received initial metadata from client: {metadata_str}")


    def client_init(self, request, context):
        print(f"Performing client initialization")
        self.print_metadata(context)
        # Get request ID
        request_id = self.get_request_id(context)
        # Check if request_id is cached
        if request_id in self.response_cache:
            cached_response = self.return_cached_response(request_id, context)
            print(f"Cached response found for request {request_id}. It is {cached_response}")
            if cached_response == 0:
                response = lock_pb2.Response(status=lock_pb2.Status.WORKING_ON_IT)
                print(f"Returning response {response}")
                return response
            print(f"Returning cached response {cached_response}")
            return cached_response
        # If request_id is not cached, cache the response_ID, process it, cache the response and then return the response
        print(f"No cache response found for request {request_id}. Processing request")
        self.initialise_cache(request_id)
        print(f"Initialised cache with request {request_id} and value {self.response_cache[request_id]}")
        with self.lock:
            # simulate slow server
            print(f"Simulating slow server: sleeping for 5 seconds")
            time.sleep(5)
            print(f"Server finished sleeping")
            self.client_counter += 1
            client_id = self.client_counter
        response = lock_pb2.Response(status= lock_pb2.Status.SUCCESS, id_num=client_id)
        print(f"Response is {response}")
        self.update_cache(request_id, response)
        print(f"The updated cache is {self.response_cache}")
        # Testing packet loss
        if random.random() < 0:
            print("Simulating packet loss: dropping response from server")
            # Set long time to simulate packet loss
            time.sleep(15)
        print(f"Server has finished processing request {request_id}. Client ID is {client_id}")
        print(f"Returning response {response}")
        return response
    
    def client_close(self, request, context):
        self.print_metadata(context)
        # Get request ID and check if request is cached
        request_id = self.get_request_id(context)
        cached_response = self.return_cached_response(request_id, context)
        if cached_response:
            return cached_response
        # If request is not cached, process request and cache response
        with self.lock:
            if self.lock_owner == request.rc:
                self.locked = False
                self.condition.notify_all()
                self.lock_owner = None
                print(f"Lock released due to client {request.rc} closing.")
        
            response = lock_pb2.Response(status=lock_pb2.Status.SUCCESS)
            self.cache_response(request_id, response)
            print(f"Client {request.rc} closed") #How else to close?
            return response
    
    def lock_acquire(self, request, context):
        print(f"Performing lock acquisition")
        self.print_metadata(context)
        # Get request ID and check if request is cached
        request_id = self.get_request_id(context)
        cached_response = self.return_cached_response(request_id, context)
        if cached_response:
            return cached_response
        # If request is not cached, process request and cache response
        with self.condition:
            while self.locked:
                print(f"Client {request.client_id} waiting for lock.")
                self.condition.wait()
            self.locked = True
            self.lock_owner = request.client_id
            response = lock_pb2.Response(status=lock_pb2.Status.SUCCESS)
            self.cache_response(request_id, response)
            print(f"Lock granted to client {request.client_id}")
            return response
        
    def lock_release(self, request, context):
        self.print_metadata(context)
        # Get request ID and check if request is cached
        request_id = self.get_request_id(context)
        cached_response = self.return_cached_response(request_id, context)
        if cached_response:
            return cached_response
        # If request is not cached, process request and cache response
        with self.condition:
            if self.locked and self.lock_owner == request.client_id:
                self.locked = False
                self.lock_owner = None
                self.condition.notify_all()
                response = lock_pb2.Response(status=lock_pb2.Status.SUCCESS)
                self.cache_response(request_id, response)
                print(f"Lock released by client {request.client_id}")
                return response
            elif not self.locked:
                response = lock_pb2.Response(status=lock_pb2.Status.FILE_ERROR)
                self.cache_response(request_id, response)
                print(f"Client {request.client_id} attempted to release a lock that was not acquired.")
                return response #Not a file error but all we have in proto?
            else:
                response = lock_pb2.Response(status=lock_pb2.Status.FILE_ERROR)
                self.cache_response(request_id, response)
                print(f"Client {request.client_id} attempted to release a lock owned by client {self.lock_owner}.")
                return response #Again Not file error
    
    def file_append(self, request, context):
        print(f"Performing file append")
        self.print_metadata(context)
        # Get request ID and check if request is cached
        request_id = self.get_request_id(context)
        cached_response = self.return_cached_response(request_id, context)
        if cached_response:
            # Simmulating packet loss
            print("Simulating packet loss: dropping response from server")
            if random.random() < 0.3:
                time.sleep(15)
            return cached_response
        else:
            response = lock_pb2.Response(status=lock_pb2.Status.WORKING_ON_IT)
            return response
        # If request is not cached, process request and cache response
        if self.lock_owner != request.client_id:
            response = lock_pb2.Response(status=lock_pb2.Status.FILE_ERROR)
            self.cache_response(request_id, response)
            print(f"Client {request.client_id} does not have access to lock")
            if random.random() < 0.7:
                print("Simulating packet loss: dropping response from server")
                time.sleep(15)
            return response
        if request.filename not in self.files:
            response = lock_pb2.Response(status=lock_pb2.Status.FILE_ERROR)
            self.cache_response(request_id, response)
            print(f"Filename {request.filename} does not exist")
            if random.random() < 0.7:
                print("Simulating packet loss: dropping response from server")
                time.sleep(15)
            return response
        print(f"Client {request.client_id} appended to file {request.filename}")
        with open(request.filename, 'ab') as file:
            # Simulating slow server
            print(f"Simulating slow server: sleeping for 20 seconds")
            time.sleep(20)
            file.write(request.content)
        response = lock_pb2.Response(status=lock_pb2.Status.SUCCESS)
        self.cache_response(request_id, response)
        if random.random() < 0.7:
            print("Simulating packet loss: dropping response from server")
            time.sleep(15)
        return response
    
if __name__ == "__main__":
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=100))
    lock_pb2_grpc.add_LockServiceServicer_to_server(LockService(), server)
    server.add_insecure_port(port)
    server.start()
    print("Server started (localhost) on port 56751.")
    server.wait_for_termination()