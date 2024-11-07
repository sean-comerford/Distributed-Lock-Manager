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
        call_counter = 1
        print(f"intercept_unary_unary has been called {call_counter} times")
        call_counter += 1
        # Generate unique request ID
        unique_request_id = str(uuid.uuid4())
        # Set the initial timeout
        initial_timeout = 10
        # Set the max timeout
        max_timeout = 20


        # Retry loop
        for attempt in range(self.max_attempts):
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
                response = continuation(client_call_details, request)
                print(f"response is {response}")
                if isinstance(response, grpc._channel._InactiveRpcError):
                    raise response
                
                if isinstance(response, grpc._interceptor._UnaryOutcome):
                    print(f"Only unwrapping if response is a UnaryOutcome")
                    actual_response = response.result()
                    print(f"Unwrapped response is {actual_response}")
                else:
                    actual_response = response
                #print(f"Type of actual_response: {type(actual_response)}, attributes: {dir(actual_response)}")


                # Check if server is still working on request, if so, increase timeout
                # Timeout is the time the server has to give the client a response
                # If the client knows the server is working on it, then we increase the timeout to allow the server more time
                if actual_response.status == lock_pb2.Status.WORKING_ON_IT:
                    print(f"Server is still processing the request attempt {attempt + 1}/{self.max_attempts}. Increasing timeout.")
                    # Increasing timeout for the next attempt, up to a max limit
                    initial_timeout = 10
                    #initial_timeout = min(initial_timeout * 2, max_timeout)
                    print(f"Waiting before next retry")
                    time.sleep(10)
                    continue
                else:
                    print(f"Returning response {actual_response}")
                    return actual_response  # Successful call, return the response
            except grpc.RpcError as e:
                print(f"Error has been raised: {e}")
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
                    print(f"Retry attempt {attempt} failed with {e.code()}. Retrying in {delay} seconds.")
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
