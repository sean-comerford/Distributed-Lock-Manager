import json
import os
import lock_pb2
class Logger:
    def __init__(self, filepath="log_server_1.json"):
        self.filepath = filepath
    
    def serialize_cache(self,cache):
        def serialize_tuple(response):
            """Serializes a tuple response (e.g., filename and content)."""
            if len(response) == 2:
                filename, content = response
                # Decode bytes to a string
                return {'filename': filename, 'content': content.decode('utf-8')}
            return None  # Handle invalid or empty tuples

        return {
            request_id: (
                response.status  # If response is lock_pb2.Response, use its status
                if not isinstance(response, tuple) 
                else serialize_tuple(response)  # Otherwise, serialize the tuple
            )
            for request_id, response in cache.items()
        }



    def save_log(self, lock_owner, lock_counter, cache, counter, locked):
        state = {
            "lock_owner": lock_owner,
            "lock_counter": lock_counter,
            "locked": locked,
            "client_counter": counter,
            "cache": self.serialize_cache(cache)
        }
        with open(self.filepath, "w") as f:
            json.dump(state, f)

    def load_log(self):
        if not os.path.exists(self.filepath):
            return None, 0, {}, 0, False
        with open(self.filepath, "r") as f:
            state = json.load(f)
        return state["lock_owner"], state["lock_counter"], state["cache"], state["client_counter"], state["locked"]