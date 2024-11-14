import json
import os

class Logger:
    def __init__(self, filepath="log_server_1.json"):
        self.filepath = filepath

    def save_log(self, lock_owner, lock_counter, cache, counter, locked):
        state = {
            "lock_owner": lock_owner,
            "lock_counter": lock_counter,
            "locked": locked,
            "client_counter": counter,
            "cache": {request_id: (response.status if response is not None else response)
            for request_id, response in cache.items()}
        }
        with open(self.filepath, "w") as f:
            json.dump(state, f)

    def load_log(self):
        if not os.path.exists(self.filepath):
            return None, 0, {}, 0, False
        with open(self.filepath, "r") as f:
            state = json.load(f)
        return state["lock_owner"], state["lock_counter"], state["cache"], state["client_counter"], state["locked"]