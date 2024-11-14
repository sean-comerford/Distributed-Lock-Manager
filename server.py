import grpc
from concurrent import futures
import time
import threading
import lock_pb2
import lock_pb2_grpc
import random
import asyncio
import logging
from collections import OrderedDict
import argparse
from logger import Logger
import queue
import sys
from datetime import datetime, timedelta

timeout = 100
port = '127.0.0.1:56751'



class LockService(lock_pb2_grpc.LockServiceServicer):


    def __init__(self,deadline=8,drop=False,load=False):
        if(load):
            self.logger = Logger()
            self.load_server_state_from_log(drop=False, deadline=8)
        else:
            self.locked = False #Is Lock locked?
            self.lock = threading.Lock() #Mutual Exclusion on shared resources (self.locked, client_counter and lock_owner)
            self.condition = threading.Condition(self.lock) #Coordinate access to the lock by allowing threads (clients) to wait until lock availabel
            self.client_counter = 0
            self.lock_owner = None
            self.files = {f'file_{i}.txt': [] for i in range(100)} #Change to however we want out files to look
            # Cache to store the processed requests and their responses
            self.response_cache = OrderedDict()
            self.cache_lock = threading.Lock()
            self.logger = Logger()
            self.lock_counter = 0
            self.drop = drop
            self.periodic_thread = threading.Thread(target=self._execute_periodically, daemon=True)
            self.periodic_thread.start()
            self.log_queue = queue.Queue()
            self.logging_thread = threading.Thread(target=self.log_processor, daemon=True)
            self.logging_thread.start()
            self.last_action_time = None
            self.deadline = timedelta(seconds=deadline)
            self.start_cache_clear_thread()

    def log_processor(self):
        while True:
            log_data = self.log_queue.get()
            try:
                self.logger.save_log(*log_data)
                print("Logged state:" )
            except Exception as e:
                print(f"Error logging state: {e}")
            self.log_queue.task_done()

    def log_state(self):
        self.log_queue.put((self.lock_owner, self.lock_counter, self.response_cache, self.client_counter, self.locked))

    def _execute_periodically(self):
        """Executes the periodic task every `self.deadline` seconds.
        this thread checks that if a lock owner has been set
        if so, it waits for the deadline to pass and if the lock owner is still the same
        it removes the lock from that client
        
        """
        while True:
            if self.lock_owner is not None and self.last_action_time is not None:
                # Check how long has elapsed since the last action
                time_elapsed = datetime.now() - self.last_action_time 
                if time_elapsed > self.deadline:
                    with self.lock:
                        self.locked = False
                        self.lock_owner = None
                        self.last_action_time = None
                        self.condition.notify_all()
                    print("LOCK OWNER OVER DEADLINE, REMOVING LOCK")
            # Check every second if the lock owner has been over the deadline
            time.sleep(1)

    def start_cache_clear_thread(self):
        '''Start a thread to clear the oldest requests from the cache every 30 minutes'''
        def clear_cache():
            while True:
                time.sleep(1800)
                self.clear_oldest_half_of_cache()
                print(f"Oldest half of cache cleared")
        thread = threading.Thread(target=clear_cache, daemon=True)
        thread.start()

    def clear_oldest_half_of_cache(self):
        '''Clear the oldest half of the cache'''
        with self.cache_lock:
            cache_size = len(self.response_cache)
            items_to_remove = cache_size // 2
            for _ in range(items_to_remove):
                self.response_cache.popitem(last=False)

    def get_request_id(self, context):
        '''Helper method to get request ID from client'''
        for key, value in context.invocation_metadata():
            if key == "request-id":
                return value
    
    def return_cached_response(self, request_id, context):
        '''Return cached response if available, otherwise return 0'''
        return self.response_cache[request_id]

    def initialise_cache(self, request_id):
        '''Initialise cache with key = request_id and value =  0'''
        # This value will be updated when the server finishes processing the request
        self.response_cache[request_id] = None


    def update_cache(self, request_id, response):
        '''Store response in cache keyed by request_id'''
        self.response_cache[request_id] = response


    def print_metadata(self, context):
        '''Helper method to print metadata from client'''
        metadata_str = ", ".join(f"{key}={value}" for key, value in context.invocation_metadata())
        #print(f"Received initial metadata from client: {metadata_str}")


    def process_request(self, context):
        '''Process request from client to see if it has been cached etc.'''
        # Print metadata
        self.print_metadata(context)
        # Get request ID
        request_id = self.get_request_id(context)
        # Check if request_id is cached
        if request_id in self.response_cache:
            cached_response = self.return_cached_response(request_id, context)
            # If the request_id is cached but its value hasnt been updated yet (i.e value is None), server is still working on request
            if cached_response == None:
                response = lock_pb2.Response(status=lock_pb2.Status.WORKING_ON_IT)
                print(f"Server is slow and still working on request {request_id}.")
                return response
            # If the request_id is cached and its value has been updated (i.e. value is not None), return the response
            print(f"Cached response found for request {request_id}. Returning response")
            return cached_response
        # If request_id is not cached, initialise the cache with the request_id and set the response to None, then proceed to process the request
        print(f"No cache response found for request {request_id}. Processing request")
        self.initialise_cache(request_id)
        return None

    def load_server_state_from_log(self, drop=False, deadline=8):
        print("Server Loading from logs")
        self.lock_owner, self.lock_counter, self.response_cache, self.client_counter, self.locked = self.logger.load_log()
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.files = {f'file_{i}.txt': [] for i in range(100)}
        self.response_cache = OrderedDict()
        self.cache_lock = threading.Lock()
        self.logger = Logger()
        self.drop = drop
        self.periodic_thread = threading.Thread(target=self._execute_periodically, daemon=True)
        self.periodic_thread.start()
        self.log_queue = queue.Queue()
        self.logging_thread = threading.Thread(target=self.log_processor, daemon=True)
        self.logging_thread.start()
        self.deadline = deadline
        self.start_cache_clear_thread()


    def client_init(self, request, context):
        '''Initialise client'''
        # Process request
        response = self.process_request(context)
        if response:
            return response
        # If there is no response ready, process the request and create a response
        request_id = self.get_request_id(context)
        with self.lock:
            # Process request
            self.client_counter += 1
            client_id = self.client_counter
        response = lock_pb2.Response(status= lock_pb2.Status.SUCCESS, id_num=client_id)
        self.update_cache(request_id, response)
        print(f"Server has finished processing request {request_id}. Client ID is {client_id}, response is {response}")
        return response
    
    def client_close(self, request, context):
        '''Close client'''
        # Process request
        response = self.process_request(context)
        if response:
            return response
        # If there is no response ready, process the request and create a response
        request_id = self.get_request_id(context)
        with self.lock:
            # If the client closing is the lock owner, release the lock
            if self.lock_owner == request.rc:
                self.locked = False
                self.condition.notify_all()
                self.lock_owner = None
                print(f"Lock released due to client {request.rc} closing.")
            # If the client closing is not the lock owner, just close the client
            response = lock_pb2.Response(status=lock_pb2.Status.SUCCESS)
            self.update_cache(request_id, response)
            print(f"Client {request.rc} closed") #How else to close?
            return response
    
    def lock_acquire(self, request, context):
        # Process request
        response = self.process_request(context)
        if response:
            return response
        # If there is no response ready, process the request and create a response
        request_id = self.get_request_id(context)
        if self.drop == "1":
                print(f"\n\n\nSIMULATED ARRIVAL PACKET LOSS {request_id}.")
                self.drop = False
                time.sleep(4)
                
        with self.condition:
            while self.locked:
                print(f"Client {request.client_id} waiting for lock.")
                self.condition.wait()
            self.locked = True
            self.lock_owner = request.client_id
            self.lock_counter += 1
            self.last_action_time = datetime.now()
            response = lock_pb2.Response(status=lock_pb2.Status.SUCCESS,id_num=self.lock_counter)
            self.update_cache(request_id, response)
            self.log_state()
            print(f"Lock granted to client {request.client_id}")
            if self.drop == "2":
                print(f"\n\n\nSIMULATED RETURN PACKET LOSS {request_id}.")
                self.drop = False
                time.sleep(4)
            return response
        
    def lock_release(self, request, context):
        # Process request
        response = self.process_request(context)
        if response:
            return response
        # If there is no response ready, process the request and create a response
        request_id = self.get_request_id(context)
        with self.condition:
            if self.locked and self.lock_owner == request.client_id and self.lock_counter == request.lock_val:
                self.locked = False
                self.lock_owner = None
                self.last_action_time = None
                self.condition.notify_all()
                response = lock_pb2.Response(status=lock_pb2.Status.SUCCESS)
                self.update_cache(request_id, response)
                self.log_state()
                print(f"Lock released by client {request.client_id}")
                return response
            elif not self.locked:
                response = lock_pb2.Response(status=lock_pb2.Status.FILE_ERROR)
                self.update_cache(request_id, response)
                print(f"Client {request.client_id} attempted to release a lock that was not acquired.")
                return response #Not a file error but all we have in proto?
            else:
                response = lock_pb2.Response(status=lock_pb2.Status.FILE_ERROR)
                self.update_cache(request_id, response)
                print(f"Client {request.client_id} attempted to release a lock owned by client {self.lock_owner}.")
                return response #Again Not file error
    
    def file_append(self, request, context):
        # Process request
        response = self.process_request(context)
        if response:
            return response
        # If there is no response ready, process the request and create a response
        request_id = self.get_request_id(context)
        if self.lock_counter != request.lock_val or self.lock_owner == None:
            response = lock_pb2.Response(status=lock_pb2.Status.LOCK_EXPIRED)
            self.update_cache(request_id, response)
            print(f"Client {request.client_id} has an expired lock")
            return response
        if  self.lock_owner != request.client_id:
            response = lock_pb2.Response(status=lock_pb2.Status.LOCK_NOT_ACQUIRED)
            self.update_cache(request_id, response)
            print(f"Client {request.client_id} does not have access to lock")
            return response
        if request.filename not in self.files:
            response = lock_pb2.Response(status=lock_pb2.Status.FILE_ERROR)
            self.update_cache(request_id, response)
            print(f"Filename {request.filename} does not exist")
            return response
        with open(request.filename, 'ab') as file:
            file.write(request.content)
        response = lock_pb2.Response(status=lock_pb2.Status.SUCCESS)
        self.last_action_time = datetime.now()
        self.update_cache(request_id, response)
        print(f"Client {request.client_id} appended to file {request.filename}")
        return response
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LockClient operations")
    parser.add_argument(
        "-d", "--drop",
        type=int,
        choices=[1, 2],  # Limit acceptable values to 1 or 2
        help="Drop packet on lock acquire: 1=lost on the way there, 2=lost on the way back"
    )
    parser.add_argument(
        "-l", "--load",
    )
    args = parser.parse_args()
    
    if args.load == "1":
        load = True
    else:
        load = False
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=100))
    if args.drop==1:
        lock_pb2_grpc.add_LockServiceServicer_to_server(LockService(drop="1",load=load), server)
    elif args.drop==2:
        lock_pb2_grpc.add_LockServiceServicer_to_server(LockService(drop="2",load=load), server)
    else:
        lock_pb2_grpc.add_LockServiceServicer_to_server(LockService(drop=False,load=load), server)
    server.add_insecure_port(port)
    server.start()
    print("Server started (localhost) on port 56751.")
    server.wait_for_termination()