#!/usr/bin/env python3

from helperS import *

'''
usage: ./server.py <port> <max_fail_attempts>

example usage:
    ./server.py 12000 5
    python3 server.py 12000 5

This script and the related helper file contains all
necessary functionality to run a server instance.
It utilises multi-threading to host multiple client
instances and basic locks to handle concurrency.

'''


def main():
    '''
    Main function that listens for incoming
    connections and spawns new threads. 

    Borrowed from Python Socket
    programming tutorial 
    (link in report)
    '''

    # set up server
    CONN = getConnection()
    PORT = int(CONN.port)
    ATTEMPTS = int(CONN.fail_attempts)
    HOST = ''
    server = TCPServer(HOST, PORT)

    # intialise logs
    setupLogs()
    
    # create thread for new connections
    server.host()
    
    # create lock for basic concurrency
    lock = threading.Lock()

    # listen for incoming connnections
    while True:

        try:
            client, addr = server.accept()
            newThread = threading.Thread(
                target=clientThread,
                args=(client, addr, ATTEMPTS, lock)
                )
            newThread.start()
            device_count = threading.activeCount() - 1
            LogPrint(
                    f'has connected. [ACTIVE: {device_count}]',
                    addr
                    )
        except KeyboardInterrupt:
            break

    server.shutdown()


def clientThread(client, addr, MAX_ATTEMPTS, lock):
    '''
    Spawn a new client thread.
    '''

    # set up static variables
    IP, _ = addr
    COMMANDS = ('UED', 'SCS', 'DTE', 'AED', 'OUT', 'UVF')
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
                message =\
                        'Your account has been blocked. ' +\
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

                clientUser.send('Welcome!\n\n')
                lock.release()
                continue

            failedAttempts += 1
            connected, message =\
                checkFailedStatus(
                            failedAttempts,
                            MAX_ATTEMPTS,
                            user,
                            AUTH_USERS,
                            blocked
                            )

            clientUser.send(message)
            lock.release()

        elif authenticated:   # successfully authenticated

            try:
                recvMsg = clientUser.receive()
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
            connected, message = execCommand(
                    recvMsg,
                    user,
                    active,
                    clientUser
                    )
            clientUser.send(message)
            lock.release()

    clientUser.logout()


if __name__ == '__main__':
    main()