#!/usr/bin/env python3

from helperC import *

'''
usage: ./client.py <ip address> <port> <UDP Port>

example usage:
    ./client.py 127.0.0.1 12000 5432
    python3 client.py 127.0.0.1 12000 5432

Run an client instance.
Implementation details can be found in
helperC.py.
'''


def main():

    prompt = 'Enter one of the following commands ' +\
            '(EDG, UED, SCS, DTE, AED, OUT, UVF): '

    connection = getConnection()
    host, port, udp = connection.host, int(connection.port), connection.udpPort
    client = ClientInstance(host, port, udp)
    client.connect()

    lock = threading.Lock()
    connected = True
    authenticated = False
    loggedInUser = None

    while connected:

        if not authenticated:
            loggedInUser, password = getLogin(loggedInUser)
            client.tcpSend(f'{loggedInUser} {password} {udp}')

            '''Case where we exit before we login'''

            if loggedInUser == 'OUT' and password == 'OUT':
                break

            recvMsg = client.tcpRecv()
            print(recvMsg, end='')

            connected, authenticated = checkLoginStatus(recvMsg)
            if authenticated:

                '''Successful authentication'''

                udpConn = client.udpServer(loggedInUser, udp, lock)
                client.login(loggedInUser)

        else:
            try:
                input_message = input(prompt)
                command = re.split(r'\s', input_message)[0]

                if command == 'EDG':
                    success, error =\
                            client.EDG(input_message, loggedInUser)
                    if not success:
                        print(error, end='')
                    continue

                if command == 'UED':

                    '''
                    Upload data files. No query is sent
                    to the server if an error occurs.
                    '''

                    success, message =\
                        client.UED(input_message, loggedInUser)
                    if not success:
                        print(message)
                        continue
                else:
                    client.tcpSend(input_message)

                if command == 'OUT':

                    '''Disconnect from server.'''

                    connected = False

                recvMsg = client.tcpRecv()

                if command == 'UVF':

                    '''Upload file to another client'''

                    success, error =\
                        client.UVF(input_message, recvMsg, udpConn)
                    if not success:
                        print(error, end='')
                    continue

                if 'DISCONNECTED' in recvMsg:

                    '''
                    Confirmation from server
                    of OUT request.
                    '''
                    connected = False

                print(recvMsg, end='')

            except (EOFError, KeyboardInterrupt, TypeError):
                client.tcpSend('OUT')
                recvMsg = client.tcpRecv()
                print('\n' + recvMsg, end='')
                break

    client.disconnect()


if __name__ == '__main__':
    main()
