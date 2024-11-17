import json
import os
import lock_pb2
class Logger:
    def __init__(self, filepath="log_server_1.json"):
        self.filepath = filepath
    
    def serialize_cache(self,cache):
        def serialize_tuple(response):
            """Serializes a tuple response (e.g., filename and content)."""
            if response is None:
                return "none"
            if isinstance(response, int):
                return response
            if len(response) == 2:
                try:
                    filename, content = response
                except (UnicodeDecodeError, AttributeError):
                    filename,content = response
                
                # Decode bytes to a string
                return {'filename': filename, 'content': content}
            return None  # Handle invalid or empty tuples

        # if response is none return none, if response response.status, if tuple serialize it
        return {
            request_id: (
                response.status  # If response is lock_pb2.Response, use its status
                if isinstance(response, lock_pb2.Response) 
                else serialize_tuple(response)  # Otherwise, serialize the tuple
            )
            for request_id, response in cache.items()
        }



    def save_log(self, lock_owner, lock_counter, cache, counter, locked):
        print(cache)
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