import grpc
import lock_pb2
import lock_pb2_grpc
import argparse

class LockClient:
    def __init__(self):
        self.channel = grpc.insecure_channel('localhost:56751')
        self.stub = lock_pb2_grpc.LockServiceStub(self.channel)
        self.client_id = None

    def RPC_init(self):
        request = lock_pb2.Int()
        response = self.stub.client_init(request)
        self.client_id = response.rc
        print(f"Successfully connected to server with client ID: {self.client_id}")
            
    def RPC_lock_acquire(self):
        request = lock_pb2.lock_args(client_id=self.client_id)
        response = self.stub.lock_acquire(request)
        print(f"Lock acquired")

    def RPC_lock_release(self):
        print(f"Attempting to release lock with client ID: {self.client_id}")
        request = lock_pb2.lock_args(client_id=self.client_id)
        response = self.stub.lock_release(request)
        print(f"Lock released")

    def RPC_append_file(self, file, content):
        request = lock_pb2.file_args(filename = file , content = bytes(content, 'utf-8'), client_id=self.client_id) # Specify content to append
        response = self.stub.file_append(request)
        if response.status == lock_pb2.Status.SUCCESS:
            print(f"File appended")
        elif response.status == lock_pb2.Status.LOCK_NOT_ACQUIRED:
            print(f"Client does not have access to lock")
        elif response.status == lock_pb2.Status.FILE_ERROR:
            print(f"Filename does not exist")
        #print(f"File appended/failed") #Error handling for different responses (goes for all rpc calls)

    def RPC_close(self):
        request = lock_pb2.Int(rc=self.client_id)
        response = self.stub.client_close(request)
        print("Client connection closed.")

# Interactive command loop for testing and debugging
def command_loop(client):
    print("Entering interactive mode. Type 'help' for a list of commands. Type 'exit' to quit.")
    while True:
        cmd = input("Enter command: ").strip().lower()
        if cmd == "init":
            client.RPC_init()
        elif cmd == "acquire":
            client.RPC_lock_acquire()
        elif cmd == "append":
            filename = input("Enter filename: ").strip()
            content = input("Enter content: ").strip()
            client.RPC_append_file(filename, content)
        elif cmd == "release":
            client.RPC_lock_release()
        elif cmd == "close":
            client.RPC_close()
            break  # Exit loop after closing
        elif cmd == "help":
            print("Available commands:")
            print("init     : Initialize the client and get client ID")
            print("acquire  : Acquire the lock")
            print("append      : Append to a file")
            print("release  : Release the lock")
            print("close    : Close the client connection and exit")
        elif cmd == "exit":
            print("Exiting interactive mode.")
            break
        else:
            print(f"Unknown command: {cmd}. Type '--help' for a list of commands.")


if __name__ == "__main__":
    # Argument to start in interactive mode
    parser = argparse.ArgumentParser(description="LockClient operations")
    parser.add_argument("-i", "--interactive", action="store_true", help="Enter interactive mode")
    args = parser.parse_args()

    # Initialize client and enter command loop if interactive mode is selected
    client = LockClient()
    if args.interactive:
        command_loop(client)
