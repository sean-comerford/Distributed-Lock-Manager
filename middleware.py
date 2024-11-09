#from client_library import LockClient 
import grpc
import random
import threading
import time
import logging
import asyncio
from typing import Callable
import uuid
import lock_pb2

    
class RetryInterceptor(grpc.UnaryUnaryClientInterceptor):
    def __init__(self, max_attempts=5, initial_backoff=0.1, max_backoff=1.0, backoff_multiplier=2, retryable_status_codes=None):
        self.max_attempts = max_attempts
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_multiplier = backoff_multiplier
        self.retryable_status_codes = retryable_status_codes or {grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED}

    def _retry_delay(self, attempt):
        """Calculates the delay based on attempt and backoff multiplier."""
        return min(self.initial_backoff * (self.backoff_multiplier ** attempt), self.max_backoff)

    def intercept_unary_unary(self, continuation: Callable, client_call_details, request):
        # Generate unique request ID
        unique_request_id = str(uuid.uuid4())

        # Retry loop
        for attempt in range(self.max_attempts):
            if attempt == 0:
                print(f"Initial attempt")
            else:
                print(f"Retry number {attempt} ")

            # Add retry count to metadata, or if it is already there, update the retry attempt number
            metadata = list(client_call_details.metadata or [])

            retry_attempt_found = False
            for i, (key, value) in enumerate(metadata):
                # Check if "retry-attempt" key is already in metadata
                if key == "retry-attempt":
                    metadata[i] = (key, str(attempt))
                    retry_attempt_found = True
                    break
            
            # If "retry-attempt" key is not in metadata, add it	
            if not retry_attempt_found:
                metadata.append(("retry-attempt", str(attempt)))
            
            # Check if "request-id" key is already in metadata. If not, add it
            if not any (key == "request-id" for key, _ in metadata):
                metadata.append(("request-id", unique_request_id))

            # Update client_call_details with modified metadata and timeout if this is the first attempt
            client_call_details = client_call_details._replace(
                metadata=metadata,
                timeout=2  # Set the call timeout to 10 seconds
            )


            response = None
            try:
                # Interceptor receives the response back from the server
                response = continuation(client_call_details, request)
                # If the response is an error (e.g. a timeout waiting for the server to respond), raise the error
                if type(response) == grpc._channel._InactiveRpcError:
                    # Raise error to begin retry procedure
                    raise response
                # If the response is a UnaryOutcome, unwrap it to get the actual response
                elif isinstance(response, grpc._interceptor._UnaryOutcome):
                    actual_response = response.result()
                else:
                    print(f"Unexpected response from the server: {response}")
                
                # If the response status is WORKING_ON_IT, sleep for 5 seconds and try again
                if actual_response.status == lock_pb2.Status.WORKING_ON_IT:
                    print(f"Server is still working on request, delaying before retrying")
                    time.sleep(2)
                    # Skip this iteration and move to the next iteration.
                    if attempt < self.max_attempts - 1:
                        continue
                    else:
                        # If the max attempts have been reached and the server is still working on the request, raise an error
                        # May include switching to a different server in the future.
                        raise grpc.RpcError("Max attempts reached")
                    
                if actual_response.status == lock_pb2.Status.LOCK_NOT_ACQUIRED:
                    print(f"Lock not acquired, must acquire lock before appending file")
                    return response
                    
                # If the response is not an error or WORKING_ON_IT, return the response to the client
                print(f"Response received from server, returning response to client {actual_response}")
                return response
                
                #return response  # Successful call, return the response
            except grpc.RpcError as e:
                # If the status code is not in retryable codes, raise the error
                if e.code() not in self.retryable_status_codes:
                    raise

                # If we've reached the max attempts, raise the error
                if attempt == self.max_attempts - 1:
                    raise

                # Wait before retrying
                delay = self._retry_delay(attempt)
                if attempt == 0:
                    print(f"Initial attempt failed with {e.code()}. Retrying in {delay} seconds.")
                else:
                    print(f"Retry {attempt + 1} failed with {e.code()}. Retrying in {delay} seconds.")
                time.sleep(delay)

        return response
'''
client = LockClient(interceptor=RetryInterceptor())
logging.basicConfig(level=logging.INFO)
logging.basicConfig()
client.RPC_init()
time.sleep(5)
print(f"{client.client_id}")
time.sleep(5)
client.RPC_close()
#client.RPC_lock_acquire()

#client.RPC_lock_release()

#client.RPC_close()
'''