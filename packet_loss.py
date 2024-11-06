#from client_library import LockClient 
import grpc
import random
import threading
import time
import logging
import asyncio
from typing import Callable

    
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
        # Retry loop
        for attempt in range(self.max_attempts):
            # Add retry count to metadata, or if it is already there, update the retry attempt number
            metadata = list(client_call_details.metadata or [])

            # Check if "retry-attempt" key is already in metadata
            updated = False
            for i, (key, value) in enumerate(metadata):
                if key == "retry-attempt":
                    metadata[i] = (key, str(attempt))
                    updated = True
                    break
            
            # If "retry-attempt" key is not in metadata, add it	
            if not updated:
                metadata.append(("retry-attempt", str(attempt)))

            # Update client_call_details with modified metadata and timeout if this is the first attempt
            client_call_details = client_call_details._replace(
                metadata=metadata,
                timeout=2  # Set the call timeout to 10 seconds
            )

            response = None
            try:
                response = continuation(client_call_details, request)
                if type(response) == grpc._channel._InactiveRpcError:
                    raise response
                return response  # Successful call, return the response
            except grpc.RpcError as e:
                # If the status code is not in retryable codes, raise the error
                if e.code() not in self.retryable_status_codes:
                    raise

                # If we've reached the max attempts, raise the error
                if attempt == self.max_attempts - 1:
                    raise

                # Wait before retrying
                delay = self._retry_delay(attempt)
                print(f"Retry attempt {attempt + 1} failed with {e.code()}. Retrying in {delay} seconds.")
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
