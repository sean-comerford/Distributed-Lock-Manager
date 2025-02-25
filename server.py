import grpc
from concurrent import futures
import time
import threading
import lock_pb2
import lock_pb2_grpc
import random
import asyncio
import logging
from collections import OrderedDict, deque
import argparse
from logger import Logger
import queue
import sys
from datetime import datetime, timedelta
import pickle 
import uuid
import glob
import os

from enum import Enum
from concurrent.futures import ThreadPoolExecutor

import json



# Server setup
ports = [
            '127.0.0.1:56751',
            '127.0.0.1:56752',
            '127.0.0.1:56753'
]

# Raft states
class State(Enum):
    FOLLOWER = 1
    CANDIDATE = 2
    LEADER = 3

class LockService(lock_pb2_grpc.LockServiceServicer):

# Initialse the server
    def __init__(self,port="127.0.0.1:56751",deadline=4,drop=False,load=False,ensure_leader=True,single=False):
        if(load):
            # Wipe all files, as we assume they are lost on a server crash and must be rebuilt from the persistant log
            for subdir in os.listdir("./filestore"):
                subdir_path = os.path.join("./filestore", subdir)
                if os.path.isdir(subdir_path):
                    txt_files = glob.glob(os.path.join(subdir_path, "*.txt"))
                    for txt_file in txt_files:
                        os.remove(txt_file)
                        print(f"Deleted {txt_file} after server crash")
            print(f"All files deleted after server crash")
            open("./filestore/56751/file_1.txt", 'w').close()

            # Load the server state from the log
            self.logger = Logger(filepath="./filestore/"+str(port[-5:])+"/"+str(port[-5:])+".json")
            self.ensure_leader = ensure_leader
            self.single=single
            self.load_server_state_from_log( deadline=4)
            
        else:
            # Intialise the lock as unlocked
            self.locked = False
            self.lock = threading.Lock() #Mutual Exclusion on shared resources (self.locked, client_counter and lock_owner)
            self.condition = threading.Condition(self.lock) #Coordinate access to the lock by allowing threads (clients) to wait until lock availabel
            # Monotonically increasing counter to track the initialisation number of a client
            self.client_counter = 0
            self.lock_owner = None
            self.files = {f'file_{i}.txt': [] for i in range(100)}
            # Flag to allow server to be restarted not as leader FOR TESTING PURPOSES
            self.ensure_leader=ensure_leader
            self.single=single
            # Initialise the raft attributes
            self.init_raft(port)
            # Cache to store the processed requests and their responses
            self.response_cache = OrderedDict()
            # Ensuring one client can add to response cache at a time
            self.cache_lock = threading.Lock()
            # Logger to save the state of the server
            self.logger = Logger(filepath="./filestore/"+str(port[-5:])+"/"+str(port[-5:])+".json")
            # Monothonically increasing counter to track the number of locks given out
            # Also used a proxy for index/version of the logs
            self.lock_counter = 0
            # Background thread to trigger global lock timeout
            self.periodic_thread = threading.Thread(target=self._execute_periodically, daemon=True)
            self.periodic_thread.start()
            # Background thread to save the logs when they get updated
            self.log_queue = queue.Queue()
            self.logging_thread = threading.Thread(target=self.log_processor, daemon=True)
            self.logging_thread.start()
            # Time of the last operation that was performed. For tracking lock timeouts
            self.last_action_time = None
            # Deadline for lock timeout
            self.deadline = timedelta(seconds=deadline)
            # Background thread to clear the oldest half of the response cache every 30 minutes
            self.start_cache_clear_thread()
            # Cache to store the critical section operations before they are performed.
            # These operations will be performed when receiving an RPC_lock_release request
            self.cs_cache = {}
            # Counter to keep track of all the replicas that have updated their log to match the primary
            # Set to 1 as the primary is always up to date with its own log
            self.log_updated_reply_counter = 1
            # Deadline for replica to respond to the primary
            self.update_log_deadline = 2
            # Boolean to determine if the system is available or not
            self.system_available = True
            # Port numbers for the other servers in the cluster
            self.available_ports = [56751,56752,56753]
            # Track the status of the replica ports
            self.port_status = {}

            # replication setup
            port_numbers = port[-5:]
            self.folderpath = "./filestore/"+str(port_numbers)
            # Make the filestore directory if it does not exist
            if not os.path.exists(self.folderpath):
                os.makedirs(self.folderpath)

            self.replicas = []  # List to store LockServiceStubs for each replica
            self.queues = []  # List to store queues for each replica
            
            # Dynamically create channels and associated stubs and queues for n replicas
            self.available_ports = [56751,56752,56753]
            self.available_ports.remove(int(port_numbers))
            for i in range(len(self.available_ports)):
                p = self.available_ports[i]
                channel = grpc.insecure_channel(f'localhost:{p}')
                stub = lock_pb2_grpc.LockServiceStub(channel)
                self.replicas.append(stub)
                self.queues.append(deque())
        # After initialisation, log the state of the server
        self.log_state()

    def RPC_sendFullLog(self, revived_replica):
        '''Send the full log to a replica once it comes back online'''
        print(f"Sending full log to replica")

        try:
            # Load the log from the logger
            lock_owner, lock_counter, cache, counter, locked = self.logger.load_log()

            # Serialize the log data using the logger class
            data = pickle.dumps((lock_owner, lock_counter, cache, counter, locked))
            # Request is send with the serialised critical section and the new lock counter value
            request = lock_pb2.ByteMessage(data=data, lock_val=self.lock_counter) 

            # Send the serialized data to the replica and check the response
            with grpc.insecure_channel(revived_replica) as channel:
                stub = lock_pb2_grpc.LockServiceStub(channel)
                response = stub.receiveFullLog(request)
                
                # Check response from replica server
                if response.status == lock_pb2.Status.FULL_LOG_UPDATED:
                    print(f"FULL LOG SUCCESSFULLY SENT TO NEWLY ONLINE REPLICA")
                else:
                    print(f"FULL LOG FAILED TO SEND TO NEWLY ONLINE REPLICA")
        
        except grpc.RpcError as e:
            print(f"Failed to send full log to replica at {revived_replica}: {e}")
        except Exception as e:
            print(f"Error sending full log: {e}")

    def receiveFullLog(self, request, context):
        '''Receive the full log from the primary server and rebuilds the newly online replica server from it'''
        print("-----SERVER RECEIVED FULL LOG-----")
        try:
            # Deserialize the received data
            lock_owner, lock_counter, cache, counter, locked = pickle.loads(request.data)
            self.lock_owner = lock_owner
            self.lock_counter = lock_counter
            self.response_cache = cache
            self.client_counter = counter
            self.locked = locked
            print(f"Replica successfully updated log")

            # Write the updated state to the replica's log file
            self.logger.save_log(
            lock_owner=self.lock_owner,
            lock_counter=self.lock_counter,
            cache=self.response_cache,
            counter=self.client_counter,
            locked=self.locked
            )
            # Rebuild the replica from the primary servers log
            # Write the appends to the corresponding files, creating the files if they dont already exist
            self.rebuild_replica()
            response = lock_pb2.Response(status=lock_pb2.Status.FULL_LOG_UPDATED)
            return response
        except Exception as e:
            # Handle errors during deserialization
            print("Replica error when updating log:", str(e))


    def RPC_sendBytes(self):
        '''Send a completed critical section to be duplicated on the replicas'''
        # Serialize the queue data to bytes
        self.log_updated_reply_counter = 1
        if self.role==State.LEADER and not self.single:
            # There is one self.queues list for each replica
            # Iterate through each of the replicas and their queue
            for i, queue in enumerate(self.queues):
                print(f"Queue {i}")
                if len(queue) == 0:
                    print(f"Queue {i+1} is empty, skipping...")
                    data = ""
                    
                
                data = pickle.dumps(list(queue))  # Serialize the queue
                # Request is send with the serialised critical section and the new lock counter value
                request = lock_pb2.ByteMessage(data=data, lock_val=self.lock_counter)
                
                # Send serialized data to the corresponding replica
                replica_stub = self.replicas[i]  # Get the stub for the corresponding replica
                attempt = 0
                success = False
                max_attempts = 5
                successful_attempt = False

                # Perform retries if the replica does not respond
                while attempt < max_attempts + 1 and successful_attempt == False:
                    try:
                        response = replica_stub.sendBytes(request)

                        # Check response from replica server
                        if response.status == lock_pb2.Status.LOG_UPDATED:
                            self.log_updated_reply_counter += 1
                            print(f"REPLICATION SUCCESSFUL for replica {i+1}")
                            queue.clear()
                            success = True
                            break
                        else:
                            print(f"REPLICATION FAILED for Replica {i+1}, Will retry with {attempt+ 1} out of {max_attempts}...")
                            successful_attempt = False

                    except grpc._channel._InactiveRpcError as e:
                        if attempt == max_attempts - 1:
                            print(f"REPLICATION FAILED for Replica {i+1}. Max attempts reached.")
                            break
                        else:
                            print(f"REPLICATION FAILED for Replica {i+1}. Will retry with {attempt+ 1} out of {max_attempts}...")
                            time.sleep(0.5)
                    
                    attempt += 1
                    
                if not success:
                    print(f"Not successful in replicating to replica {i+1}.")
                    # If the replica has not updated its log, do not clear the queue and continue to the next replica
                    continue
                
            # Check if enough replicas have updated their logs
            if self.log_updated_reply_counter > len(self.replicas) // 2:
                print(f"Majority of replicas have updated their logs. Log updated successfully.")
                self.system_available = True
            else:
                # What to do if enough replicas have not updated their logs
                print(f"Majority of replicas have not updated their logs. Log update failed.")
                self.system_available = False
                print(f"--------------------------SYSTEM UNAVAILABLE--------------------------")


    def sendBytes(self, request, context):
        '''Receive and append a completed critical section to the replica's log'''
        print("-----SERVER RECEIVED BYTES-----")
        
        try:
            # Deserialize the received data
            received_data = pickle.loads(request.data)
            print(f"Updated lock counter to {request.lock_val} from {self.lock_counter}")
            # Update internal lock counter to new value
            self.lock_counter = request.lock_val
            # Print each entry in the deserialized data
            print(f"The critical section in received data is {received_data}")

            # Iterate through each critical section in the received data and append it to the file and the response cache
            for cs in received_data:
                if cs != "":
                    for append_request_id, (filename, content) in cs.items():
                        if type(content) == bytes:
                            content = str(content, 'utf-8')
                        print(f"Appending content TYPE {type(content)} to file {filename}")    
                        with open(self.folderpath+"/"+filename, 'a') as file:
                            file.write(content)
                            self.update_cache(append_request_id,(filename,content))
                            print(f"Appended {content} to file {filename}")
                else:
                    continue
            self.log_state()
            
            print(f"Replica successfully updated log")
            response = lock_pb2.Response(status=lock_pb2.Status.LOG_UPDATED)
            return response

                    
        
        except Exception as e:
            # Handle errors during deserialization
            print("Replica error when updating log:", str(e))
    

    def init_raft(self, port):
        '''Initialise the raft specific attributes'''
        self.port = port
        self.heartbeat_timeout=1
        self.term = 0
        self.leader = None
        if self.port == "127.0.0.1:56751" and self.ensure_leader:
            print("DEFAULT LEADER SET TO 56751")
            self.role = State.LEADER
            self.leader = self.port
            self.term = 1
            # Sends a heartbeat to all other servers to show that leader is still online
            if not self.single:
                self.broadcast_heartbeat()
        else:
            self.role = State.FOLLOWER
            # Replica servers time to receive a heartbeat from the leader server. 
            self.reset_timer()
        
        self.voted_for = None
        
        self.timeout = random.uniform(2,3)
        
        
    
    def reset_heartbeat_timer(self):
        '''Resets the time for the leader to send a heartbeat'''
        if hasattr(self, 'heartbeat_timer') and self.heartbeat_timer is not None:
            self.heartbeat_timer.cancel()
        if(self.role==State.LEADER):
            self.heartbeat_timer = threading.Timer(self.heartbeat_timeout, self.broadcast_heartbeat)
            self.heartbeat_timer.start()
        
    def reset_timer(self):
        '''If a replica server does receive a heartbeat from the leader within the timeout, it will start an election'''
        if hasattr(self, 'election_timer'):
            self.election_timer.cancel()
        self.election_timer = threading.Timer(random.uniform(2,3), self.start_election)
        self.election_timer.start()

    def start_election(self):
        '''Starts an election to try and become the leader'''
        print("Starting Election")
        self.term += 1
        # Proposer becomes a candidate and votes for itself
        self.role = State.CANDIDATE
        self.voted_for = self.port
        self.votes_received = 1

        # Concurrently request votes from all other servers
        # If a response is received, call handle_vote_response to process it
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(self.RPC_request_vote, peer): peer
                for peer in ports
                if peer != self.port
            }
            for future in futures:
                try:
                    response = future.result()
                    self.handle_vote_response(response)
                except Exception as e:
                    print(f"Error while requesting vote from {futures[future]}: {e}")

        # If still not the leader after handling all responses, reset timer for next election
        if self.role != State.LEADER:
            self.voted_for = None
            self.reset_timer()


    def RPC_request_vote(self, peer):
        '''Get a vote from a peer server, passing the term, ports and lock counter as metadata'''
        with grpc.insecure_channel(peer) as channel:
            stub = lock_pb2_grpc.LockServiceStub(channel)
            request = lock_pb2.raft_request_args(
                term=self.term,
                candidate_id=self.port,
                last_log_index=self.lock_counter
            )
            try:
                print(f"Requesting vote from {peer}")
                response = stub.request_vote(request)
                print(f"Response received from {peer}: {response}")
                return response
            except grpc.RpcError:
                print(f"Could not send request to {peer}")
                raise 


    def handle_vote_response(self, response):
        '''Candidate gathers responses from other servers and determines if it has enough votes to become the leader'''
        if response.term > self.term:
            self.term = response.term
            self.role = State.FOLLOWER
            self.voted_for = None
            self.reset_timer()
        elif response.vote_granted:
            self.votes_received += 1
            if self.votes_received > len(ports) // 2:  # Majority votes
                self.role = State.LEADER
                self.leader = self.port
                print(f"Node {self.port} is elected as leader.")
                self.broadcast_heartbeat()

        
    def request_vote(self, request, context):
        '''Server received RPC_vote_request and decides if they should vote for the candidate'''
        response = lock_pb2.raft_response_args(term=self.term, vote_granted=False)
        # If the candidate has a higher term, the server will become a follower
        if request.term > self.term:
            self.term = request.term
            self.role = State.FOLLOWER
            self.voted_for = None
        # If the server has not yet voted, or it voted for the candidate already, and the candidate has a log that is at least as up to date as itself, 
        # Vote for the candidate and reset the timer
        if (self.voted_for is None or self.voted_for == request.candidate_id) and request.last_log_index >= self.lock_counter:
            response.vote_granted = True
            self.voted_for = request.candidate_id
            self.reset_timer()
        return response
        
    def broadcast_heartbeat(self):
        '''Distribute heartbeat to all servers, sent by the leader'''
        for peer in ports:
            if(peer != self.port):
                threading.Thread(target=self.RPC_heartbeat, args=(peer,)).start()
        self.reset_heartbeat_timer()
        
    def RPC_heartbeat(self, peer):
        '''RPC function to create and send heartbeat'''
        # Create a connection to peer server
        with grpc.insecure_channel(peer) as channel:
            stub = lock_pb2_grpc.LockServiceStub(channel)
            request = lock_pb2.raft_request_args(term=self.term, candidate_id=self.port)
            try:
                # Get response from peer server
                response = stub.heartbeat(request)
                port = peer[-5:]  # Extract the port number of the peer
                # Track the previous state of the peer
                previous_status = self.port_status.get(port, False)
                # Check if the port has transitioned from offline(false) to online(true), i.e. it has come online
                if not previous_status:
                    # Send log from primary server to newly online replica
                    print(f"Port {peer[-5:]} is online. Sending bytes.")
                    self.RPC_sendFullLog(peer)
                    print(f"Sent bytes to {peer}")

                self.port_status[peer[-5:]] = True
                # Handle the heartbeat response from the peer
                self.heartbeat_response(response)
            except grpc.RpcError:
                # Set the status of the peer to False (dead)
                self.port_status[peer[-5:]] = False
                print("Could not send hearbeat to", peer)
            
    def heartbeat_response(self, response):
        '''Handle the response from the peer'''
        # If the term from the peer is higher, the leader will become a follower
        if response.term > self.term:
            self.term = response.term
            self.role = State.FOLLOWER
            self.voted_for = None
            self.reset_timer()
            
    def heartbeat(self, request, context):
        '''Receiving an RPC_heartbeat from the leader and becoming a follower if the term from the leader is greater or equal to its own term'''
        response = lock_pb2.raft_heartbeat_args(term=self.term, success=True)
        if request.term >= self.term:
            self.term = request.term
            self.role = State.FOLLOWER
            self.leader_id = request.candidate_id
            self.reset_timer()
        else:
            response.success = False
        return response
    
    def log_processor(self):
        '''Get the log state and save it to a log file'''
        while True:
            log_data = self.log_queue.get()
            try:
                self.logger.save_log(*log_data)
                print("Logged state" )
            except Exception as e:
                print(f"Error logging state: {e}")
            self.log_queue.task_done()

    def log_state(self):
        '''Get the current state of the server and put onto the log queue'''
        self.log_queue.put((self.lock_owner, self.lock_counter, self.response_cache, self.client_counter, self.locked))

    def _execute_periodically(self):
        """Executes the periodic task every self.deadline seconds.
        this thread checks that if a lock owner has been set
        if so, it waits for the deadline to pass and if the lock owner is still the same
        it removes the lock from that client
        """
        while True:
            if self.lock_owner is not None and self.last_action_time is not None:
                # Check how long has elapsed since the last action
                time_elapsed = datetime.now() - self.last_action_time 
                if time_elapsed > self.deadline:
                    self._lock_release(lock_timeout=True)
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
    
    def initialise_cs_cache(self, request_id, filename, content):
        '''Initialise cache with key = request_id, value = (filename, content)'''
        if request_id not in self.cs_cache:
            self.cs_cache[request_id] = (filename, content)


    def update_cache(self, request_id, response):
        '''Store response in cache keyed by request_id'''
        self.response_cache[request_id] = response


    # FOR TESTING PURPOSES
    def print_metadata(self, context):
        '''Helper method to print metadata from client'''
        metadata_str = ", ".join(f"{key}={value}" for key, value in context.invocation_metadata())
        #print(f"Received initial metadata from client: {metadata_str}")


    def process_request(self, request, context):
        '''Process request from client to see if it has been cached etc.'''
        if self.system_available == False:
            response = lock_pb2.Response(status=lock_pb2.Status.SYSTEM_UNAVAILABLE)
            return response
        # Print metadata
        self.print_metadata(context)
        # Get request ID
        request_id = self.get_request_id(context)
        # Check if request_id is cached
        if request_id in self.cs_cache:
            print(f"Append operation is in the critical section cache. Waiting for lock release.")
            response = lock_pb2.Response(status=lock_pb2.Status.WAITING_FOR_LOCK_RELEASE)
            return response
        if request_id in self.response_cache:
            cached_response = self.return_cached_response(request_id, context)
            # If the request_id is cached but its value hasnt been updated yet (i.e value is None), server is still working on request
            if cached_response == None:
                response = lock_pb2.Response(status=lock_pb2.Status.WORKING_ON_IT)
                print(f"Server has seen this request before {request_id}.")
                if self.lock_owner == request.client_id and self.lock_counter == request.lock_val:
                    self.last_action_time = datetime.now()
                    print(f"Lock timeout has been updated")
                return response
            # If the request_id is cached and its value has been updated (i.e. value is not None), return the response
            print(f"Cached response found for request {request_id}. Returning response")
            if self.lock_owner == request.client_id and self.lock_counter == request.lock_val:
                self.last_action_time = datetime.now()
                print(f"Lock timeout has been updated")
            return cached_response
        # If request_id is not cached, initialise the cache with the request_id and set the response to None, then proceed to process the request
        self.initialise_cache(request_id)
        return None

    def load_server_state_from_log(self, drop=False, deadline=4):
        '''When recovering a single server from the persistant log, load the server state from this persistant log'''
        print("Server Loading from logs")
        self.lock_owner, self.lock_counter, self.response_cache, self.client_counter, self.locked = self.logger.load_log()
        
        self.client_counter = 0
        self.lock = threading.Lock() #Mutual Exclusion on shared resources (self.locked, client_counter and lock_owner)
        self.condition = threading.Condition(self.lock) #Coordinate access to the lock by allowing threads (clients) to wait until lock availabel
        self.files = {f'file_{i}.txt': [] for i in range(100)} #Change to however we want out files to look
        self.init_raft(port)
        # Cache to store the processed requests and their responses
        self.cache_lock = threading.Lock()
        
        self.periodic_thread = threading.Thread(target=self._execute_periodically, daemon=True)
        self.periodic_thread.start()
        self.log_queue = queue.Queue()
        self.logging_thread = threading.Thread(target=self.log_processor, daemon=True)
        self.logging_thread.start()
        self.last_action_time = None
        self.deadline = timedelta(seconds=deadline)
        self.start_cache_clear_thread()
        self.cs_cache = {}
        self.log_updated_reply_counter = 1
        # Deadline for replica to respond to the primary
        self.update_log_deadline = 2
        # Boolean to determine if the system is available or not
        self.system_available = True
        self.available_ports = [56751,56752,56753]
        self.port_status = {}

        # replication setup
        port_numbers = port[-5:]
        self.folderpath = "./filestore/"+str(port_numbers)
        if not os.path.exists(self.folderpath):
            os.makedirs(self.folderpath)

        self.replicas = []  # List to store LockServiceStubs for each replica
        self.queues = []  # List to store queues for each replica
        
        # Dynamically create channels and associated stubs and queues for n replicas
        self.available_ports = [56751,56752,56753]
        self.available_ports.remove(int(port_numbers))
        for i in range(len(self.available_ports)):
            p = self.available_ports[i]
            channel = grpc.insecure_channel(f'localhost:{p}')
            stub = lock_pb2_grpc.LockServiceStub(channel)
            self.replicas.append(stub)
            self.queues.append(deque())
        self.rebuild_files()
    
    
    def rebuild_files(self):
        '''When recovering a single server from the persistant log, this function will write of the persistant log into the files'''
        to_remove = []
        for key, value in self.response_cache.items():
            # Check if the value is a dictionary containing 'filename' and 'content'
            if isinstance(value, dict) and 'filename' in value and 'content' in value:
                filename = value['filename']
                content = value['content']
                to_remove.append(key)
                # Write the content to the file
                with open(self.folderpath+"/"+filename, 'a') as file:
                    file.write(content)
                print(f"Appended content to {filename}.")
            else:
                print(f"Skipping entry with key {key} as it does not contain a file definition.")
        for key in to_remove:
                del self.response_cache[key[:-2]]
                self.response_cache[key[:-2]] = self.response_cache.pop(key)
        self.log_state()

    def rebuild_replica(self):
        '''Rebuild the replicas from the received primary server's log, when the replica server comes back online'''
        # First write should overwrite the file on the newly online replica
        created_files = []
        for key, value in self.response_cache.items():
            # Check if the value is a dictionary containing 'filename' and 'content'
            if isinstance(value, dict):
                filename = value['filename']
                content = value['content']
                # Write the content to the file
                if filename not in created_files:
                    with open(self.folderpath+"/"+filename, 'w') as file:
                        file.write(content)
                    created_files.append(filename)
                else:
                    with open(self.folderpath+"/"+filename, 'a') as file:
                        file.write(content)
                    print(f"Appended content to {filename}.")
            else:
                print(f"Skipping entry with key {key} as it does not contain a file definition.")


        # Log the updated state
        self.log_state()
        print("Files rebuilt and cache updated.")


    def get_leader(self,request,context):
        '''Received an RPC request from the client to see if the server is the leader'''
        if self.role == State.LEADER:
            return lock_pb2.leader(status=lock_pb2.Status.SUCCESS, server=self.port)
        else:
            return lock_pb2.leader(status=lock_pb2.Status.NOT_LEADER, server=None)

    def client_init(self, request, context):
        '''Initialise client'''
        # Process request
        response = self.process_request(request, context)
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
        response = self.process_request(request, context)
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
        '''Accompying function to RPC_lock_acquire'''
        # Process request
        response = self.process_request(request, context)
        if response:
            return response
        # If there is no response ready, process the request and create a response
        request_id = self.get_request_id(context)
        
                
        with self.condition:
            while self.locked:
                print(f"Client {request.client_id} waiting for lock.")
                self.condition.wait()
            self.locked = True
            self.lock_owner = request.client_id
            self.lock_counter += 1
            self.last_action_time = datetime.now()
            print(f"Lock timeout has been updated")
            response = lock_pb2.Response(status=lock_pb2.Status.SUCCESS,id_num=self.lock_counter)
            self.update_cache(request_id, response)
            self.log_state()
            print(f"Lock granted to client {request.client_id}")
            
            return response
        
    def _lock_release(self, lock_timeout=False):
        '''Accompying function to RPC_lock_release'''
        # if critical section not finished drop it
        # check change to files and queues complete
        with self.condition:
            self.locked = False
            self.lock_owner = None
            print(f"Lock owner has been set to None")
            self.last_action_time = None
            self.condition.notify_all()
            # Only append to the queue if the release was explicity called by the client and not a lock timeout
            if self.role==State.LEADER and lock_timeout == False:
                for queue in self.queues:
                    queue.append(self.cs_cache)
            self.log_state()
            if self.role==State.LEADER:
                print(f"Send bytes being called after lock release")
                self.RPC_sendBytes()
                print(f"Send bytes has been called after a lock release")
            self.cs_cache.clear()
        
    def lock_release(self, request, context):
        '''Accompying function to RPC_lock_release'''
        # Process request
        response = self.process_request(request, context)
        if response:
            return response
        # If there is no response ready, process the request and create a response
        release_request_id = self.get_request_id(context)
        if self.locked and self.lock_owner == request.client_id and self.lock_counter == request.lock_val:
            # Perform the appends in the critical section cache
            for append_request_id, (filename, content) in self.cs_cache.items():
                print(f"Appending {content} to file {filename}")
                try:
                    with open(self.folderpath + "/" + filename, 'ab') as file:
                        file.write(content)
                        print(f"Appended {content} to file {filename}")
                except Exception as e:
                    print(f"Error writing to file {filename}: {e}")
                    raise  # Re-raise to propagate error if necessary

                # Update the "Response" cache with the response to the client for these appends
                response = lock_pb2.Response(status=lock_pb2.Status.SUCCESS)
                self.update_cache(append_request_id, response)
                print(f"Response cache has been updated with response to client for append to {filename} with content {content}")
            # Then clear the critical section cache
            print(f"Critical section cache cleared")
            # Then release lock and clear the critical section cache
            self._lock_release()
            response = lock_pb2.Response(status=lock_pb2.Status.SUCCESS)
            self.update_cache(release_request_id, response)
            self.log_state()
            print(f"Critical section performed by server and Lock released by client {request.client_id}")
            return response
        elif not self.locked:
            response = lock_pb2.Response(status=lock_pb2.Status.FILE_ERROR)
            self.update_cache(release_request_id, response)
            print(f"Client {request.client_id} attempted to release a lock that was not acquired.")
            return response
        else:
            response = lock_pb2.Response(status=lock_pb2.Status.FILE_ERROR)
            self.update_cache(release_request_id, response)
            print(f"Client {request.client_id} attempted to release a lock owned by client {self.lock_owner}.")
            return response
    
    def file_append(self, request, context):
        '''Accompying function to RPC_file_append'''
        # Process request
        response = self.process_request(request, context)
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
        # Store request in Critical section cache
        self.initialise_cs_cache(request_id, request.filename, request.content)
        print(f"Append operation cached in cs cache")
        print(request.filename,request.content,self.folderpath + "/" + self.port[-5:]+".json")
        self.update_cache(request_id+"-a",(request.filename, request.content.decode("utf-8")))
        #print(self.response_cache)
        self.log_state()
        print("REAL LOG UPDATED WITH APPEND")
        # Return a message to the client to release the lock to confirm the append
        # Once server receives lock_release from client, it will perform all the appends in the critical section cache
        # Then the critical section cache will be cleared, ready for the next critical section
        # The main "Response" cache will then be updated with the response to the client for these appends and the lock_release. See lock_release method
        response = lock_pb2.Response(status=lock_pb2.Status.WAITING_FOR_LOCK_RELEASE)
        # replica data added to queue

        self.last_action_time = datetime.now()
        print(f"Lock timeout has been updated")
        return response
        
    
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="LockClient operations")
    parser.add_argument(
        "-l", "--load",
    )
    parser.add_argument(
        "-p", "--port", type=int, choices=[56751, 56752, 56753], required=True, help="Port for Raft node"
    )

    parser.add_argument(
        "-x", "--xd",
    )
    parser.add_argument(
        "-s", "--singleserver",
    )
    
    args = parser.parse_args()
    
    if args.load == "1":
        load = True
    else:
        load = False
    if args.port:
        port="127.0.0.1:"+str(args.port)
    else:
        port="127.0.0.1:"+str(56751)
    if args.xd:
        ensure_leader=False
    else:
        ensure_leader=True
    single=False
    if args.singleserver:
        single=True
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=100))
    lock_pb2_grpc.add_LockServiceServicer_to_server(LockService(drop=False,load=load,port=port, ensure_leader=ensure_leader,single=single), server)
    server.add_insecure_port(port)
    server.start()
    print(f"Server started (localhost) on port {port}.")
    server.wait_for_termination()