from helperS import *


def main():
    CONN = getConnection()
    PORT = int(CONN.port)
    ATTEMPTS = int(CONN.fail_attempts)
    HOST = ''
    server = TCPServer(HOST, PORT)
    #
    # intialise logs
    # setupLogs()
    #
    # create thread for new connections
    server.host()
    #
    # create lock for basic concurrency
    lock = threading.Lock()
    clients = {}
    #
    # listen for incoming connnections
    while True:

        try:
            client, addr = server.accept()
            # clients[client] = addr
            newThread = threading.Thread(
                target=clientThread,
                args=(client, addr, ATTEMPTS, lock, clients)
            )
            newThread.start()
            device_count = threading.active_count() - 1
            LogPrint(
                f'has connected. [ACTIVE: {device_count}] \n',
            )
        except KeyboardInterrupt:
            break

    server.shutdown()


def clientThread(client, addr, MAX_ATTEMPTS, lock, clients):
    '''
    Spawn a new client thread.
    '''

    # set up static variables
    IP, _ = addr
    COMMANDS = ('msgto', 'activeuser', 'creategroup', 'joingroup', 'groupmsg', 'logout', 'p2pvideo')
    AUTH_USERS = fetchCredentials()

    clientUser = ClientInstance(client, addr)

    # set up block list instance
    blocked = BlockList()

    # set up connection variables
    failedAttempts = 0
    connected = True
    loggedInUser = None
    authenticated = False

    while connected:
        print("connected")

        if not authenticated:

            recvMessage = clientUser.receive()
            lock.acquire()

            try:
                user, password, udp = recvMessage
                if user == 'OUT' and password == 'OUT':
                    break
            except ValueError:
                # all invalid options
                print('value error')
                user = ''
                password = ''

            if blocked.check(user):
                message = \
                    'Your account has been blocked. ' + \
                    'Please try again later.\n'
                clientUser.send(message)
                lock.release()
                break

            successfulLogin = authenticateUser(AUTH_USERS, user, password)

            if successfulLogin:
                loggedInUser = user
                clientUser.loggedIn(loggedInUser)
                authenticated = True

                # update active log
                active = ActiveList(loggedInUser, IP, udp)
                # print('welcome client user is {}'.format(clientUser))
                clientUser.send('Welcome!\n\n')
                lock.release()
                continue

            failedAttempts += 1
            connected, message = \
                checkFailedStatus(
                    failedAttempts,
                    MAX_ATTEMPTS,
                    user,
                    AUTH_USERS,
                    blocked
                )

            clientUser.send(message)
            lock.release()

        elif authenticated:  # successfully authenticated
            if user not in clients.keys():
                clients[user] = clientUser
            try:
                recvMsg = clientUser.receive()
                print('the command from client is {}\n'.format(recvMsg))

                lock.acquire()
                LogPrint(' '.join(recvMsg), loggedInUser)
            except Exception as e:
                print(f'Unexpected error occurred: {e}')
                clientUser.send(str(e))
                break
            if not checkCommand(recvMsg, COMMANDS):
                clientUser.send('Invalid command\n')
                lock.release()
                continue
            print('the command from client is {}\n'.format(recvMsg))
            # connected, message, clientUser = execCommand(
            connected, sender_msg, receiver_msg, sender_client, receiver_client = execCommand(
                recvMsg,
                user,
                active,
                clientUser,
                clients
            )
            # print('current socket is {} connected is {} msg is {}'.format(clientUser, connected, message))
            # clientUser.send('hello world!\n\n')
            if receiver_client:
                receiver_client.send(receiver_msg)
            sender_client.send(sender_msg)
            lock.release()

    clientUser.logout()


if __name__ == '__main__':
    main()

# import threading, json
# from socket import *
# import os
# from collections import defaultdict
# import re
# import time


# online_user = []
# retry_max = 5

#
# class Server:
#     def __init__(self):
#         # init the data
#         self.threads = defaultdict(list)
#         # {'threadtitle1': ['msg1', 'msg2', 'msg3']}
#
#         print("server started")
#         serverPort = 12000
#         serverSocket = socket(AF_INET, SOCK_STREAM)
#         serverSocket.bind(('localhost', serverPort))
#         serverSocket.listen()
#         print("The server is ready to receive")
#
#         while True:
#             sock, addr = serverSocket.accept()
#             print(f"Connection established: {addr}")
#             t = threading.Thread(target=self.tcplink, args=(sock, addr))
#             t.start()
#
#     def tcplink(self, sock, addr):
#         '''
#         :param sock:
#         :param addr:
#         :return:
#         '''
#         # todo input method
#         login = False
#         login_fail_dict = {}
#         login_fail_cnt = 0
#         lock_start_time = 0
#         while not login:
#             msg = json.loads(sock.recv(1024).decode())
#             username = msg['user_name']
#             password = msg['password']
#
#             if username in login_fail_dict.keys() and login_fail_dict[username] is not None:
#                 if time.time() - login_fail_dict[username] >= 10:
#                     lock_start_time = 0
#                     login_fail_cnt = 0
#                 elif login_fail_dict[username] > retry_max:
#                     pass
#
#             if login_fail_cnt >= retry_max:
#                 if lock_start_time is None:
#                     lock_start_time = time.time()
#                 sock.send(json.dumps({"message": "User blocked. Try again later.", "status": False}).encode())
#
#             if verify(username, password):
#                 login = True
#                 sock.send(json.dumps({"message": "login success!", "status": True}).encode())
#             else:
#                 login_fail_cnt += 1
#
#                 if username in login_fail_dict.keys():
#                     login_fail_dict[username] += 1
#                 else:
#                     login_fail_dict[username] = login_fail_cnt
#
#                 sock.send(json.dumps({"message": "illegal user", "status": False}).encode())
#
#         login = True
#         try:
#             while login:
#                 msg = sock.recv(1024)
#                 if msg:
#                     print(msg.decode())
#                     # give feedback to client
#                     sock.send(f'Server have recvieved you msg: {msg.decode()}'.encode())
#
#                     if re.match('logout', msg.decode()):
#                         login = False
#                     # todo elif msg.decode() == 'XXX':
#                     #     DO_SOMETHING()
#
#                     elif 'sendfile' in msg.decode():
#                         filename = json.loads(msg.decode()).get('data').get('filename')
#                         filecontent = json.loads(msg.decode()).get('data').get('filecontent')
#                         savefile(filename, filecontent)
#                         print(f'file {filename} saved!')
#
#                     elif 'download' in msg.decode():
#                         filename = json.loads(msg.decode()).get('data').get('filename')
#                         filecontent = loadfile(filename)
#                         data = json.dumps(
#                             {'type': 'download', 'data': {'filename': filename, 'filecontent': filecontent}})
#                         sock.send(data.encode())
#                         print(f'file {filename} sent!')
#
#         except Exception as e:
#             if e is not ConnectionResetError:
#                 print(e)
#             print(f"Connection {addr} closed!")
#
#         finally:
#             sock.close()
#
#
# # I/O
# def load_users():
#     '''
#
#     :return:
#     '''
#     r = []
#     with open('credentials.txt', 'r') as file:
#         for row in file.readlines():
#             username, psw = row.strip('\n').split(' ')
#             r.append((username, psw))
#
#     return r
#
#
# def verify(username, psw):
#     print(username, psw)
#     print(load_users())
#     print((username, psw) in load_users())
#     return (username, psw) in load_users()
#
#
# def is_exist(username):
#     return any(username in tup for tup in load_users())
#
#
# def create_user(username, password):
#     with open('credentials.txt', 'a') as file:
#         file.write(f"\n{username} {password}")
#
#
# def savefile(filename, fs):
#     recv_path = 'recv_server'
#     if not os.path.exists(recv_path):
#         os.mkdir(recv_path)
#     with open(recv_path + '\\' + filename, 'w+') as file:
#         file.write(fs)
#
#
# def loadfile(filename) -> str:
#     with open('recv_server\\' + filename, 'r') as file:
#         return file.read()
#
#
# def json_to_file(data):
#     with open('data.json', 'w', encoding='utf-8') as f:
#         json.dump(data, f, ensure_ascii=False, indent=4)
#
#
# def file_to_json():
#     with open('data.json', 'r', encoding='utf-8') as f:
#         return json.load(f)
#

# if __name__ == '__main__':
#     s = Server()
