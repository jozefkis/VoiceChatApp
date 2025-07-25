from socket import *
from threading import *
from common.user import User
import pickle
import json


port = 9007
clients = []

class ClientHandler(Thread):
    def __init__(self, cl_sock, cl_address, cl_user):
        self.sock = cl_sock
        self.address = cl_address
        self.user = cl_user

        clients.append(self)
        super().__init__()
        self.start()
        self.send_online_users_to_all()
    
    
    def send_response(self, data):
        self.sock.sendall((json.dumps(data) + "\n").encode())

    def get_online_users(self):
        return [(client.user.username, client.user.status) for client in clients if client != self]

    def send_online_users_to_all(self):
        for client in clients:
            online_users = client.get_online_users()
            response = {"info": "UPDATE_ONLINE_USERS", "result":online_users}
            try:
                client.sock.sendall((json.dumps(response) + "\n").encode())
            except:
                client.sock.close()
                clients.remove(client)
                continue

    def disconnect(self):
        clients.remove(self)
        print(f"Bye, {self.user.username}!")
        self.send_online_users_to_all()
        self.sock.close()

    def change_status(self, *params):
        self.user.status = params[0]
        self.send_online_users_to_all()
        return {"info": "STATUS_CHANGED", "result":f"Status changed to: {params[0]}"}

    def get_ip(self, *params):
        self.user.status = "BUSY"
        self.send_online_users_to_all()
        response = {"info": "bzvz", "result":None}
        
        for client in clients:
            if client.user.username == params[0] and client.user.status != "BUSY":
                client.user.status = "BUSY"
                client.send_online_users_to_all()
                self.forward_call(client, self)
                break
        return response

    def forward_call(self, toClient, callFromClient):
        response = {"info": "INCOMMING_CALL", "result":{"address":callFromClient.address, "from":callFromClient.user.username}}
        toClient.sock.sendall((json.dumps(response) + "\n").encode())

    def decline_call(self, callFromClient):
        print(f"{self.user.username} is declining call from {callFromClient}")
        self.user.status = "ONLINE"
        self.send_online_users_to_all()

        for client in clients:
            if client.user.username == callFromClient:
                response = {"info": "RESPONSE_TO_CALL", "result":{"address":None, "from":self.user.username}}
                client.sock.sendall((json.dumps(response) + "\n").encode())
                break
    
    def accept_call(self, callFromClient):
        print(f"{self.user.username} is accepting call from {callFromClient}")

        for client in clients:
            if client.user.username == callFromClient:
                response = {"info": "RESPONSE_TO_CALL", "result":{"address":self.address[0], "from":self.user.username}}
                client.sock.sendall((json.dumps(response) + "\n").encode())
                break
    
    operations = {
        "DISCONNECT":disconnect,
        "GET_IP": get_ip,
        "CHANGE_STATUS": change_status, # nije u elif bloku
        "DECLINE_CALL": decline_call,
        "ACCEPT_CALL": accept_call
    }

    def run(self):
        while True:
            try:
                request = self.sock.recv(4096).decode()
                data = json.loads(request)
                print(data)
                operation = data.get("operation")
                parameters = data.get("parameters", [])
                
                if operation == "DISCONNECT":
                    self.disconnect()
                    break
                elif operation == "ACCEPT_CALL":
                    self.operations[operation](self, *parameters)
                    continue
                elif operation == "DECLINE_CALL":
                    self.operations[operation](self, *parameters)
                    continue
                elif operation == "TEST_REQUEST":
                    print("TEST")
                    continue
                elif operation == "ENDING_CALL_FOR_BOTH":
                    self.send_response(self.change_status("ONLINE"))
                    for client in clients:
                        if client.user.username == parameters[0]:
                            response = {"info": "ENDING_CALL", "result":self.user.username}
                            client.sock.sendall((json.dumps(response) + "\n").encode())
                            break
                    continue


                if operation in self.operations:
                    if parameters != []:
                        self.send_response(self.operations[operation](self, *parameters))
                    elif parameters == []:
                        self.send_response(self.operations[operation](self))
                else:
                    print(f"Invalid operation: {operation}")
                    self.sock.sendall(b"Invalid operation.")
            except timeout:
                print("Timeout reached, no data received")
                pass
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error parsing request: {e}")
                self.sock.sendall(b"Invalid request format.")
                self.sock.close()
                break
            except Exception as e:
                print(e)
                if self:
                    clients.remove(self)
                    self.send_online_users_to_all()
                    self.sock.close()
                break


def main():
    server_socket = socket(AF_INET, SOCK_STREAM)

    server_socket.bind(("", port))
    server_socket.listen(5)
    print("Server is up and running...")

    while True:
        client_sock, client_address = server_socket.accept()
        client_user = pickle.loads(client_sock.recv(4096))
        
        ch = ClientHandler(client_sock, client_address, client_user)


if __name__ == "__main__":
    main()