'''
Written by z3463079.

Helper functions to support the usage of
the server.py script.

'''

import os
import re
import sys
import socket
import os.path
import threading
import datetime
import argparse

# Static format variables
DATEFRMT = '%d %B %Y %H:%M:%S'

'''Server and Client structures'''


class TCPServer:
    """
    The TCP Connection class is used to
    represent TCP connection instances.
    """

    def __init__(self, host: str, port: int):
        self.Host = host
        self.Port = port
        self.Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.Socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEPORT,
            1)

    def host(self):
        '''
        Opens a new connection socket to receive information
        '''
        self.Socket.bind((self.Host, self.Port))
        self.Socket.listen()
        host = socket.gethostbyname(socket.gethostname())
        print(f'Accepting connections @ {host}. Connect using:\n'
              f'./client.py {host} {self.Port}')

    def accept(self):
        '''
        Blocking function that receives connections.
        '''
        return self.Socket.accept()

    def shutdown(self):
        self.Socket.shutdown(socket.SHUT_RDWR)
        self.Socket.close()


class ClientInstance:
    '''
    The client thread once a connection
    has been accepted by the listening
    function.
    '''

    def __init__(self, socket, addr, user=None):
        self.Addr = addr
        self.User = user
        self.Socket = socket

    def loggedIn(self, user):
        '''
        System login.
        '''
        self.User = user

    def logout(self):
        '''
        System log out.
        '''
        user = self.Addr
        if self.User:
            user = self.User
        LogPrint('has disconnected', user)
        self.Socket.shutdown(socket.SHUT_RD)
        self.Socket.close()

    def receive(self, type='message', HEADER=16, FORMAT='utf-8'):
        '''
        Receiving text and files via TCP.
        '''
        message = None
        length = self.Socket.recv(HEADER).decode(FORMAT)
        print('receive is {}'.format(length))
        if length:
            if type == 'message':
                message = self.Socket.recv(int(length))
                message = re.split(r'\s', message.decode(FORMAT))
                return message
            elif type == 'file':
                self.Socket.settimeout(0.1)
                try:
                    message = b''
                    while True:
                        data = self.Socket.recv(8192)
                        if not data:
                            break
                        message += data
                except socket.timeout:
                    self.Socket.settimeout(None)
                    if message:
                        LogPrint('File downloaded', self.User)
                        return message

    def send(self, message: str, HEADER=16, FORMAT='utf-8'):
        '''
        Sending bytes via TCP.

        Borrowed from the Python Socket 
        Programming Tutorial. 
        (link provided in report)
        '''
        # print('send func the msg is {}'.format(message))
        sendMessage = message.encode(FORMAT)
        msgLength = str(len(sendMessage)).encode(FORMAT)
        sendLength = msgLength + b' ' * (HEADER - len(msgLength))
        self.Socket.sendall(sendLength)
        self.Socket.sendall(sendMessage)


'''Server functionality'''


def execCommand(commandInput, user, activeUsers, socket, clients):
    '''
    Executes the required server side functionality.
    '''
    connected = True
    message = ''
    command = commandInput[0]
    receiver_socket = None
    receiver_msg = None
    if command == 'logout':
        activeUsers.disconnect(user)
        clients.pop(user, 0)
        message = f'DISCONNECTED \'{user}\'\n'
        connected = False
    elif command == 'msgto':
        date = datetime.datetime.now().strftime(DATEFRMT)
        receiver_msg, receiver_socket = MSGTO(date, commandInput, clients)
        if not receiver_msg and not receiver_socket:
            message = f'no response\n'
        else:
            message = f'message sent at {date}\n'
    elif command == 'AED':
        message = f'{activeUsers.getActive(user)}\n'
    elif command == 'SCS':
        message = SCS(commandInput, user)
    elif command == 'DTE':
        message = DTE(commandInput, user)
    elif command == 'UVF':
        message = UVF(commandInput, user, activeUsers)
    elif command == 'UED':
        message = UED(commandInput, user, socket)
    if not message:
        message = 'NONE'
    return connected, message, receiver_msg, socket, receiver_socket


def UVF(commandInput: list, user: str, activeUsers):
    '''
    return UVF details for p2p transfer
    '''
    try:
        _, otherClient, _ = commandInput[:3]
    except ValueError:
        message = 'Missing parameters. \'EdgeDevice\' and ' + \
                  '\'File\' must be provided.\n'
        return message
    message = f'\'{otherClient}\' is not currently active.\n'
    isActive = activeUsers.getUser(otherClient)
    if isActive:
        LogPrint(f'details for \'{otherClient}\' sent', user)
        message = f'{activeUsers.getUser(otherClient)[3:]}\n'
    return message


def MSGTO(date, commandInput: list, clients):
    '''
    Remote upload from edge users to the webserver.
    '''
    sender = commandInput[1]
    receiver = commandInput[2]
    # print('clients now is {}'.format(clients))
    if receiver not in clients:
        return None, None
    receiver_client = clients[receiver]
    msg = f'{date}, {sender} : {commandInput[3]}\n'
    return msg, receiver_client
    # filename = f'{user}-{fileID}.txt'
    # file = b''
    # serverSocket.Socket.settimeout(3)
    # try:
    #     data = serverSocket.receive('file')
    #     if data:
    #         file += data
    # except socket.timeout:
    #     # time out is required for no data received
    #     print('socket timed out for UED')
    #     serverSocket.Socket.settimeout(None)
    # if file:
    #     with open(filename, 'wb') as f:
    #         f.write(file)
    #     with open(filename, 'r') as f:
    #         length = len(f.readlines())
    #     date = datetime.datetime.now().strftime(DATEFRMT)
    #     with open('upload-log.txt', mode='a') as w:
    #         print('; '.join((user, date, str(fileID), str(length))), file=w)
    #     LogPrint(f'{filename} successfully downloaded.', user)
    #     return f'Success. \'{filename}\' has been uploaded to the server.\n'


def UED(commandInput: list, user: str, serverSocket):
    '''
    Remote upload from edge users to the webserver.
    '''
    fileID = commandInput[1]
    filename = f'{user}-{fileID}.txt'
    file = b''
    serverSocket.Socket.settimeout(3)
    try:
        data = serverSocket.receive('file')
        if data:
            file += data
    except socket.timeout:
        # time out is required for no data received
        print('socket timed out for UED')
        serverSocket.Socket.settimeout(None)
    if file:
        with open(filename, 'wb') as f:
            f.write(file)
        with open(filename, 'r') as f:
            length = len(f.readlines())
        date = datetime.datetime.now().strftime(DATEFRMT)
        with open('upload-log.txt', mode='a') as w:
            print('; '.join((user, date, str(fileID), str(length))), file=w)
        LogPrint(f'{filename} successfully downloaded.', user)
        return f'Success. \'{filename}\' has been uploaded to the server.\n'


def DTE(commandInput: list, user: str):
    '''
    Function that executes the deletion
    of web server files.
    '''
    # check correct number of parameters
    if len(commandInput) != 2:
        message = 'Missing parameters. \'FileID\' must be provided.\n'
        return message

    try:
        # check correct parameter type
        fileID = int(commandInput[1])
    except ValueError:
        message = 'Invalid parameter provided. ' + \
                  '\'FileID\' must be an integer.\n'
        return message

    file = f'{user}-{fileID}.txt'
    message = f'Invalid \'fileID\' provided. \'{file}\' ' + \
              'does not exist.\n'

    # check file exists
    filePath = os.path.abspath(os.path.join(os.getcwd(), file))
    fileExists = os.path.isfile(filePath)
    if not fileExists:
        return message

    message = f'Success. \'{file}\' has been removed.\n'
    date = datetime.datetime.now().strftime(DATEFRMT)
    try:
        with open(filePath, mode='r') as r:
            # this breaks when the file is not
            # a text file i.e., video, jpg, etc
            size = len(r.readlines())
    except UnicodeDecodeError:
        with open(filePath, 'rb') as r:
            size = len(r.readlines())
    with open('deletion-log.txt', mode='a') as w:
        print('; '.join((user, date, str(fileID), str(size))), file=w)
    LogPrint(f'\'{file}\' deleted.', user)
    os.remove(filePath)
    return message


def SCS(commandInput: list, user: str):
    '''
    Conduct a set of pre-defined processes
    on the webserver.
    '''

    if len(commandInput) != 3:
        # check correct number of parameters
        message = \
            'Invalid number of parameters provided. ' + \
            'Both \'fileID\' and \'computationOperation\' parameters ' + \
            'must be provided.\n'
        return message
    else:
        _, fileID, computation = commandInput[:3]
        try:
            # check correct parameter type
            fileID = int(fileID)
        except ValueError:
            message = \
                'Invalid argument for \'fileID\'. ' + \
                'This parameter must be an integer.\n'
            return message

    message = f'Invalid \'fileID\' provided. \'{user}-{fileID}.txt\' ' + \
              'does not exist.\n'

    # check file exists
    filePath = os.path.abspath(os.getcwd() + f'/{user}-{fileID}.txt')
    if not os.path.isfile(filePath):
        return message

    try:

        with open(filePath, 'r') as r:
            data = [int(num) for num in r.readlines()]

        if computation == 'SUM':
            result = sum(data)
        elif computation == 'AVERAGE':
            result = f'{sum(data) / len(data):.2f}'
        elif computation == 'MIN':
            result = min(data)
        elif computation == 'MAX':
            result = max(data)
        else:
            message = \
                'Invalid \'computation\' parameter provided. ' + \
                'Only SUM, AVERAGE, MAX, MIN are allowed.\n'
            return message
        message = f'Success. \'{computation}\' calculated ' + \
                  f'for \'{user}-{fileID}.txt\': {result}\n'
        LogPrint(f'\'{user}-{fileID}\' {computation} conducted.', user)
    except UnicodeDecodeError:
        # covers an additional edge case where the file type is not
        # a text file. Response is simply that the file does not exist.
        message = f'Invalid \'fileID\' provided. \'{user}-{fileID}.txt\' ' + \
                  'does not exist.\n'

    return message


'''List data structures'''


class BlockList:
    '''
    The BlockList class is used to contain
    an on-going list of blocked users during
    a server instance.
    '''

    blockedUsers = []

    def __init__(self, user=None):
        if user:
            BlockList.blockedUsers.append(user)

    def block(self, user: str):
        BlockList.blockedUsers.append(user)
        LogPrint('has been blocked for 10 seconds', user)

    def unblock(self, user: str):
        BlockList.blockedUsers.remove(user)
        LogPrint('has been unblocked', user)

    def check(self, user: str):
        return user in BlockList.blockedUsers


class ActiveList:
    '''
    The ActiveList class is used to hold an
    on-going list of active users during a server
    instance.
    '''

    numUsers = 1
    ActiveUsers = dict()

    def __init__(self, user: str, ipaddr: str, udp: str):
        '''
        Intialise when a user successfully logs into the server.
        '''
        date = datetime.datetime.now().strftime(DATEFRMT)
        device = str(ActiveList.numUsers)
        log = '; '.join((device, date, user, ipaddr, udp))
        ActiveList.ActiveUsers[user] = log
        ActiveList.numUsers += 1
        with open('edge-device-log.txt', mode='w') as w:
            for d in ActiveList.ActiveUsers.keys():
                print(ActiveList.ActiveUsers[d], file=w)

        activeUsers = ', '.join(
            ActiveList.ActiveUsers.keys()
        )
        LogPrint('has successfully logged in', user)
        LogPrint(f'Current active users are: {activeUsers}')

    def disconnect(self, user: str):
        '''
        Used when a user disconnects from the server instance.
        '''
        devNum = int(ActiveList.ActiveUsers.pop(user).split('; ')[0])
        ActiveList.numUsers -= 1
        for d in ActiveList.ActiveUsers.keys():
            device, date, user, ipaddr, udp = \
                ActiveList.ActiveUsers[d].split('; ')
            if int(device) > devNum:
                device = str(int(device) - 1)
            ActiveList.ActiveUsers[user] = \
                '; '.join(
                    (device, date, user, ipaddr, udp)
                )
        with open('edge-device-log.txt', mode='w') as w:
            if ActiveList.numUsers > 1:
                for d in ActiveList.ActiveUsers.keys():
                    print(ActiveList.ActiveUsers[d], file=w)
            else:
                w.write('')
        activeUsers = ', '.join(
            (device for device in ActiveList.ActiveUsers.keys())
        )
        if activeUsers:
            LogPrint(f'The remaining active users are: {activeUsers}')
        else:
            LogPrint('No active users remaining')

    def getActive(self, user: str):
        '''
        Returns all active devices.
        '''
        if len(ActiveList.ActiveUsers.keys()) > 1:
            return 'Other active edge devices are:\n' + '\n'.join(
                (', '.join(ActiveList.ActiveUsers[key].split('; ')[1:])
                 for key in ActiveList.ActiveUsers.keys()
                 if key != user))
        else:
            return 'No other active edge devices'

    def getUser(self, user: str):
        '''
        Fetches a user details if they are active.
        '''
        userExists = ActiveList.ActiveUsers.get(user)
        if userExists:
            return userExists.split('; ')
        return


'''General purpose functions'''


def getConnection():
    '''
    Command line arguments parsing.
    '''
    parser = argparse.ArgumentParser(description='Host a server connection.')
    parser.add_argument('port')
    parser.add_argument('fail_attempts')
    args = parser.parse_args()
    correctPort = re.match(r'^[0-9]+$', args.port)
    correctAttempts = re.match(r'^[0-5]$', args.fail_attempts)
    if not correctPort:
        print(f'Invalid input provided for port: \'{args.port}\'')
        sys.exit()
    if not correctAttempts:
        print('Invalid number input provided for allowed consecutive '
              f'failed attempts: \'{args.fail_attempts}\'')
        sys.exit()
    return args


def authenticateUser(logins: dict, *args):
    '''
    User authentication.
    '''
    user, password = args
    return user in logins.keys() and logins[user] == password


def fetchCredentials():
    '''
    Returns a dict of login items from credentials.txt.
    '''
    logins: dict = dict()
    with open('credentials.txt', mode='r') as users:
        for line in users:
            user, password = line.strip('\n').split(' ')
            logins[user] = password
    return logins


def checkFailedStatus(attempts, max_attempts, user, logins, block):
    '''
    Returns login status based on user details provided.
    '''

    connected = True

    if attempts == max_attempts:
        LogPrint('has reached maximum failed attempts', user)
        message = \
            'Invalid details provided. ' + \
            'Maximum attempts reached. Closing connection.\n'
        if logins.get(user):
            block.block(user)
            blockTimer = threading.Timer(
                10.0, block.unblock, args=(user,))
            blockTimer.start()
            message = \
                'Invalid details. Your account has been blocked. ' + \
                'Please try again later.\n'
        connected = False
    else:
        message = 'Invalid username. Please try again.\n'
        if logins.get(user):
            message = 'Invalid password. Please try again.\n'
    return connected, message


def checkCommand(command: str, valid_commands: tuple):
    '''
    Check if a command is valid
    '''
    print("command is {}".format(command))
    if not command:
        return False
    command = command[0]
    return command in valid_commands


def setupLogs():
    '''
    Intialises the log files.
    '''
    logs = ('edge-device-log.txt', 'deletion-log.txt', 'upload-log.txt')
    for f in logs:
        with open(f, 'w') as f:
            f.write('')


def LogPrint(message: str, user='', log='SYSTEM LOG'):
    '''
    Print log messages.
    '''
    date = datetime.datetime.now().strftime(DATEFRMT)
    if user:
        print(f"[{log}] {date} [{user}] {message}")
    else:
        print(f"[{log}] {date} {message}")
