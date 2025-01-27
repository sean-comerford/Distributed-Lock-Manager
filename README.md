# Distributed Lock Manager
This project designs a fault-tolerant and highly available append-only log that can be accessed by a distributed set of clients. This distributed lock manager ensures mutual exclusion, preventing concurrent access that could lead to inconsistencies or race conditions. It allows processes running on different nodes to synchronise their actions when accessing shared files, ensuring that onlye one process can hold a lock on a resource at any given time. It allows processes to safely acquire and release locks on shared resources. The lock manager is implemented using grpc and Python. 

## Structure
A client library is implemented with an attached interceptor. Every Remote Procedure Call (RPC) function call passes through the interceptor, whose purpose is to handle requests, retries and timeouts for all RPC calls. A bounded consistency model is implemented, which utilises the ``lock_release`` method as the trigger for duplication of server data from the leader server to the replica servers. The server library handles client requests. Message receipt is asynchronous and messages can take a long time to be delivered, can be duplicated and lost in the network. It is assumed that messages are never corrupted, and Byzantine faults are not considered. 

## Design flow
The below diagram shows the flow of RPC calls in the system in the basic case, i.e. assuming no faults in the network or system components. Whenever the client wants to append to a shared file, it must acquire the lock for that file first. The system ensures atomicity through the use of a critical section cache. Critical section tasks are appended to the critical section cache and only commited once the client calls ``lock_release``. 

![Design Flow](https://github.com/user-attachments/assets/28ced9f0-fd2c-41a3-9bca-9d157519e2f8)


<ol>
   <li>Clients initialise with the server.</li>
   <li><code>lock_acquire</code> RPC call is sent from the client and passes through the interceptor/middleware to the server.</li>
   <li>The server receives the request:
      <ol type="a">
         <li>If the lock is free, the server will send a SUCCESS message back to the client along with the id number for the lock.</li>
         <li>If the lock is currently held by someone else, the interceptor will retry the RPC request up to a maximum number of attempts. The client is blocked and will wait for the lock.</li>
      </ol>
   </li>
   <li>When a client acquires the lock, it can modify the shared file by sending a <code>file_append</code> RPC call , which again is passed through the interceptor on its way to the server.</li>
   <li>The server will then add the append request to the critical section cache, and will reply to the client with a status message WAITING_FOR_LOCK_RELEASE</li>
   <li>Client sends <code>lock_release</code> or times out:
   <ol type="a">
         <li>If client performs successful <code>lock_release</code>: the server will release the lock and perform all the operations in the critical section cache, send requests to duplicate that data on replica servers and returns SUCCESS message back to the client. </li>
         <li>If the lock times out: Server will wipe the critical section cache and send only the new lock counter to the replicas. The critical section cache will not be appended, as the critical section was not committed with an explicit <code>lock_release</code> RPC call.</li>
      </ol></li>
      <li>The server can now grant the lock to the next waiting client.</li>
      <li>The new client can modify the file. </li>
</ol>

## Fault Tolerance
### Single Server Failure
The system uses a persistent log. This log is updated with every committed critical section to ensure atomicity. The server can be fully rebuilt from the log file and will reallocate lock ownership to the appropriate client.

### Network Failure
The client may retry requests up to a maximum number of attampts. Each request from the client has a request ID. The server can recognise which requests are duplicate requests, so will crucially not execute the same append requests twice, ensuring idempotency. 

### Distributed Server Failure
When a server in a distributed cluster fails, RAFT leader election takes place to elect a new leader. This ensures fault-tolerance, the system can remain available as long as n/2 servers are available, with n being the number of servers in the cluster. Servers that have failed are rebuilt by receiving the full persistent log from the current leader.
