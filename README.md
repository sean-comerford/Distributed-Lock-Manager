## Todo List:
Client closing- I’m not sure if I did it correctly/as intended
Client Closing - While holding a lock?

Error handling - some print messages in the client say for example „file appended successfully” no matter what the return message is from the server.

Message status - I’m not sure if we can incorporate our own statuses but the proto only has SUCCESS and FILE_ERROR. Some statuses like LOCK_NOT_ACQUIRED when trying to release it or similar could be useful

Test cases- good to test on many different cases

Lock system - there’s only one lock for all the files as the document said. This means no deadlock issues. However the current implementation takes a random client waiting for the lock when another client has acquired it as deemed by the OS. Could be good to choose the next client by earliest timestamp (by adding timestamp variable to lock_args) this prevents a client waiting too long if they’re unlucky
