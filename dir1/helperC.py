
import re
import os
import socket
import os.path
import argparse
import threading
from random import randint


class ClientInstance:

    def __init__(self, host, port, udp):
        '''
        Initialise a client instance.
        '''
        self.Host = host
        self.Port = port
        self.Udp = udp
        self.Timeout = 3
        self.Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        '''
        Client connection.
        '''
        self.Socket.connect((self.Host, self.Port))

    def disconnect(self):
        '''
        Client disconnection.
        '''
        self.Socket.shutdown(socket.SHUT_RD)
        self.Socket.close()

    def login(self, user: str):
        self.User = user

    def udpServer(self, loggedInUser: str, udp: socket, lock: threading.Lock):
        '''
        Start the UDP listening server for p2p file transfers.
        '''
        ip = socket.gethostbyname(socket.gethostname())
        conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        startThread = threading.Thread(
                    target=udpServer,
                    args=(ip, udp, lock)
                    )
        startThread.setDaemon(True)
        startThread.start()
        return conn

    def udpSend(self, message: str, udpConn1: socket, udpConn2: tuple, type='msg'):
        '''
        Basic implementation of UDP communication with sequence number check.
        '''

        if type == 'msg':
            udpConn1.sendto(message.encode('utf-8'), udpConn2)
        else:
            HEADER = 16
            seqNum = 0
            while True:
                with open(message, 'rb') as f:
                    data = f.read(4080)
                    while data:
                        seqStr = str(seqNum)
                        padding = ' ' * (HEADER - len(seqStr))
                        msg = (seqStr + padding).encode('utf-8') + data
                        udpConn1.sendto(msg, udpConn2)
                        status = udpConn1.recv(HEADER).decode('utf-8')
                        while status != 'ACK' + seqStr:
                            udpConn1.sendto(msg, udpConn2)
                            status = udpConn1.recv(HEADER).decode('utf-8')
                        data = f.read(4080)
                        seqNum += 1
                    print(f'\'{message}\' sent')
                    status = str(-1)
                    padding = ' ' * (HEADER - len(status))
                    msg = (status + padding).encode('utf-8')
                    udpConn1.sendto(msg, udpConn2)
                    break

    def tcpSend(self, message, type='msg', HEADER=16, FORMAT='utf-8'):
        '''
        Sending via TCP to the web server.
        '''
        if type == 'msg':
            message = message.encode(FORMAT)
        msgLength = str(len(message)).encode(FORMAT)
        sendLength = msgLength + b' ' * (HEADER - len(msgLength))
        self.Socket.sendall(sendLength)
        self.Socket.sendall(message)

    def tcpRecv(self, HEADER=16, FORMAT='utf-8'):
        '''
        Receiving via TCP from the web server.
        '''
        timeouts = 0
        while True:
            self.Socket.settimeout(self.Timeout)
            try:
                length = self.Socket.recv(HEADER).decode(FORMAT)
                if length:
                    message = self.Socket.recv(int(length)).decode(FORMAT)
                    self.Socket.settimeout(None)
                    self.Timeout = 3
                    return message
            except socket.timeout:
                self.Timeout += 2
                timeouts += 1
                print('waiting for server response...')

    def UED(self, clientMssg: str, user: str):
        '''
        Uploading txt files to the web server.
        '''
        command = re.split(r'\s', clientMssg)
        status, message = False, None

        # check for valid num of parameters
        if not command[1:]:
            message = 'Missing parameters. \'FileID\' must be specified.'
            return status, message
        fileID = command[1]

        # check for valid integers
        if not re.match(r'^[0-9]*$', fileID):
            message = 'Invalid parameter provided. ' +\
                '\'FileID\' must be an integer.'
            return status, message
        file = f'{user}-{fileID}.txt'

        # check that file exists
        message = f'Invalid \'fileID\' provided. \'{file}\' ' +\
            'does not exist.'
        filepath = os.path.abspath(os.path.join(os.getcwd(), file))
        fileExists = os.path.isfile(filepath)
        if not fileExists:
            return status, message

        with open(file, 'rb') as r:
            data = r.read()
        self.tcpSend(clientMssg)
        self.tcpSend(data, 'file')
        return True, None

    def UVF(self, clientMssg: str, serverMssg: str, udpServer):
        '''
        Send files via UDP to other clients
        '''
        status, message = False, None
        try:
            commands = re.split(r'\s', clientMssg)

            # check the number of parameters provided
            if not commands[2:]:
                message =\
                    '\'deviceName\' and \'filename\' must be specified.\n'
                return status, message
            _, _, fileName = commands[:3]
            connectionDetails = re.split(r'\n', serverMssg)[0]
            userAddr, userPort = re.sub(
                    r'[\'\[\]]', '',
                    connectionDetails).split(',')
            udpClient = (userAddr, int(userPort))

            # check file exists
            message = f'\'{fileName}\' does not exist.\n'
            filepath = os.path.abspath(
                    os.path.join(os.getcwd(), fileName))
            fileExists = os.path.isfile(filepath)
            if not fileExists:
                return status, message

            self.udpSend(f'{self.User};;{fileName}', udpServer, udpClient)
            self.udpSend(fileName, udpServer, udpClient, 'file')
            return True, None
        except ValueError:
            # if a client is offline a message will be sent
            # instead of a integer port number resulting in a
            # value error.
            # We catch this and forward the message
            # to be printed.
            return status, connectionDetails + '\n'

    def EDG(self, commandInput: list, user: str):
        '''
        Function for conducting data generation
        at the edge device.
        '''
        status = False
        commands = re.split(r'\s', commandInput)
        # check for the correct number of arguments
        if not commands[2:]:
            message =\
                'Invalid number of parameters provided. ' +\
                'Both \'fileID\' and \'dataAmount\' parameters ' +\
                'must be provided.\n'
            return status, message
        else:
            # check for the correct number of arguments
            fileID, fileSize = commands[1:]
            try:
                fileID = int(fileID)
                fileSize = int(fileSize)
            except ValueError:
                # check for the correct parameter usage
                message = 'Invalid parameters provided. ' +\
                    '\'FileID\' and \'dataAmount\' must be integers.\n'
                return status, message

            filename = f'{user}-{fileID}.txt'
            with open(filename, mode='w') as w:
                for _ in range(fileSize):
                    print(randint(0, 999999), file=w)
        print(
            f'Success. EDG file \'{user}-{fileID}.txt\' generated.\n', end='')
        return True, None


def udpListen(loggedInUser, udp, lock):
    '''
    Set up thread for UDP listening server.
    '''
    ip = socket.gethostbyname(socket.gethostname())
    conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    startThread = threading.Thread(
                target=udpServer,
                args=(ip, udp, loggedInUser, lock)
                )
    startThread.setDaemon(True)
    startThread.start()
    return conn


def udpServer(ip, udpPort, lock, HEADER=16):
    '''
    UDP client to receive files sent via UDP.
    '''

    conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    conn.bind((ip, int(udpPort)))

    while True:
        # always wait for a file name
        file, addr = conn.recvfrom(4096)
        if file:
            lock.acquire()
            fileCheck = 0
            data = b''
            while True:
                conn.settimeout(3)
                fileData, addr = conn.recvfrom(4096)
                seqNum = int(fileData[:HEADER].decode('utf-8'))
                if seqNum < 0:
                    conn.settimeout(None)
                    break
                if fileData and seqNum == fileCheck:
                    conn.sendto(
                            ('ACK' + str(fileCheck)).encode('utf-8'),
                            addr)
                    fileCheck += 1
                    data += fileData[HEADER:]
                elif not seqNum == fileCheck:
                    conn.sendto(
                            ('NACK' + str(fileCheck)).encode('utf-8'),
                            addr)
            fileName = file.decode('utf-8')
            sender, file = fileName.split(';;')
            with open('_'.join((sender, file)), 'wb') as f:
                f.write(data)
            message = f'\n\'{file}\' received from \'{sender}\'.\n' +\
                'Enter one of the following commands ' +\
                '(EDG, UED, SCS, DTE, AED, OUT, UVF): '
            print(message, end='')
            lock.release()


def getLogin(username: str):
    '''
    Fetch the login details from stdin.
    '''
    try:
        username = input("Username: ")
        password = input("Password: ")
    except KeyboardInterrupt:
        # log out of client
        print('\r')
        return 'OUT', 'OUT'
    return username, password


def getConnection():
    '''
    Parse command line for necessary arguments.
    '''
    parser = argparse.ArgumentParser(description='Connect to a\
    server connection.')
    parser.add_argument('host')
    parser.add_argument('port')
    parser.add_argument('udpPort')
    args = parser.parse_args()
    return args


def checkLoginStatus(message: str):
    '''
    Check the connection response from the server.
    '''
    connected, authenticated = True, False
    if 'Welcome' in message:
        authenticated = True
    elif 'error' in message:
        connected = False
    elif 'blocked' in message or 'Closing' in message:
        connected = False
    return connected, authenticated
