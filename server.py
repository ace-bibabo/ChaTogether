import datetime
import re
import socket
import threading
import os
import sys

DATEFRMT = '%d %B %Y %H:%M:%S'
user_no = 0
msg_no = 0
g_msg_no = 0
msg_log_file = 'messagelog.txt'
user_log_file = 'userlog.txt'


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
        print('has been blocked for 10 seconds', user)

    def unblock(self, user: str):
        BlockList.blockedUsers.remove(user)
        print('has been unblocked', user)

    def check(self, user: str):
        return user in BlockList.blockedUsers


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


def disconnect(login_user, socket_list, send=True):
    if not login_user:
        print('>> client exit')
        return
    s = socket_list[login_user]['socket']
    if send:
        send_msg(s, 'Bye, ' + login_user + '!')
    print('>> {} logoout\n'.format(login_user))
    socket_list.pop(login_user)

    for g, elem in socket_list.items():
        if type(elem) == list:
            if login_user in elem:
                elem.remove(login_user)
                if not elem or len(elem) == 0:
                    socket_list.pop(g)
                    break

    # print('socket_list now is {}'.format(socket_list))


def read_client(s, client_name=None):
    msg = s.recv(2048).decode('utf-8')
    # print("server recv {}'s msg: {}".format(client_name, msg))
    return msg


def send_msg(s, msg):
    s.send(msg.encode('utf-8'))


def checkFailedStatus(attempts, max_attempts, user, logins, block):
    '''
    Returns login status based on user details provided.
    '''

    connected = True

    if attempts == max_attempts:
        print('has reached maximum failed attempts', user)
        message = \
            'Invalid details provided. ' + \
            'Maximum attempts reached. Closing connection.'
        if logins.get(user):
            block.block(user)
            blockTimer = threading.Timer(
                10.0, block.unblock, args=(user,))
            blockTimer.start()
            message = \
                'Invalid details. Your account has been blocked. ' + \
                'Please try again later.'
        connected = False
    else:
        message = 'Invalid username. Please try again.'
        if logins.get(user):
            message = 'Invalid password. Please try again.'
    return connected, message


def socket_target(s, socket_list, max_attmps, lock):
    failed_attempted = 0
    auth = False
    connected = True
    AUTH_USERS = fetchCredentials()
    login_user = None
    date = datetime.datetime.now().strftime(DATEFRMT)
    blocked = BlockList()
    try:
        while connected:
            content = read_client(s)
            # print('client msg is {}'.format(content))
            if not auth:
                login_user, pwd, udp_port = re.split(r'\s', content)

                if blocked.check(login_user):
                    message = \
                        'Your account is blocked due to multiple login failures. ' + \
                        'Please try again later.\n'
                    send_msg(s, message)
                    break

                verified = authenticateUser(AUTH_USERS, login_user, pwd)

                if verified:
                    auth = True
                    socket_list[login_user] = {'socket': s, 'udp_port': udp_port, 'login_time': date}
                    send_msg(s, 'Welcome to TESSENGER!')

                    LogMsg(lock,
                           login_user,
                           '; '.join((socket_list[login_user]['socket'].getsockname()[0], str(udp_port))),
                           user_log_file
                           )
                    continue

                failed_attempted += 1
                connected, message = checkFailedStatus(failed_attempted, max_attmps, login_user, AUTH_USERS, blocked)
                send_msg(s, message)

            else:
                command = re.split(r'\s', content)[0]
                print('>> {} issued {} command\n'.format(login_user, command))

                if content is None or 'logout' in content:
                    disconnect(login_user, socket_list)
                    break
                elif 'p2pvideo' == command:
                    command, receiver, filename = re.split(r'\s', content)
                    if receiver in socket_list.keys():
                        receive_port = socket_list[receiver]['udp_port']
                        addr = socket_list[receiver]['socket'].getsockname()[0]
                        msg = f'{command} {addr} {receive_port} {filename} {login_user}'
                        send_msg(s, msg)
                    else:
                        s.send((f'receiver not exists').encode('utf-8'))
                elif 'msgto' == command:
                    command, receiver, *msg = re.split(r'\s', content)

                    if (receiver not in socket_list.keys()) or (
                            receiver in socket_list.keys() and type(socket_list[receiver]) == list):
                        send_msg(s, 'user {} not online'.format(receiver))
                        continue
                    client = socket_list[receiver]['socket']
                    send_msg(s, 'message sent at ' + date)
                    new_msg = '{}, {}: {}'.format(date, login_user, ' '.join(msg))
                    send_msg(client, new_msg)

                    LogMsg(lock, login_user, ' '.join(msg), msg_log_file)
                    print('>> {} message to {} "{}" at {}\n'.format(login_user, receiver, ' '.join(msg), date))


                elif command == 'activeuser':
                    activers = []
                    for activer, prop in socket_list.items():
                        if type(prop) == list:
                            continue
                        addr = prop['socket'].getsockname()[0]
                        login_time = prop['login_time']
                        udp_port = prop['udp_port']
                        activers.append(', '.join([activer, addr, str(udp_port), login_time]))

                    msg = '.\n'.join(activers)
                    send_msg(s, msg)
                    print('>> Return active user list:\n {}\n'.format(msg))

                elif command == 'creategroup':
                    command, group_name, *mems = re.split(r'\s', content)
                    if group_name in socket_list.keys() and type(socket_list[group_name]) == list:
                        send_msg(s, f'Failed to create the group chat {group_name}: {group_name} exists!')
                        print('>> Return message Groupname {} already exists.\n'.format(group_name))
                        continue

                    active_mems = []
                    for mem in mems:
                        if mem in socket_list.keys():
                            active_mems.append(mem)

                    socket_list[group_name] = active_mems
                    send_msg(s, f'Group chat created {group_name}')
                    setupLogs(group_name)
                    print(
                        '>> Group chat room has been created, room name: {}, user in this room are: {}\n'.format(
                            group_name,
                            ','.join(
                                active_mems)))

                elif command == 'joingroup':
                    command, group_name = re.split(r'\s', content)
                    if group_name not in socket_list.keys():
                        send_msg(s, f'Groupchat {group_name} doesn’t exist.')
                        print('>> {} tries to join to a group chat that doesn’t exist.\n'.format(login_user))
                    else:
                        if login_user not in socket_list[group_name]:
                            mems = socket_list[group_name]
                            # print(mems)
                            mems.append(login_user)
                            socket_list[group_name] = mems
                            send_msg(s, f'Joined the group chat:{group_name} successfully.')
                            print(
                                '>> Return message:{} Join group chat room successfully, room name:{}, users in this room: {}\n'.format(
                                    login_user,
                                    group_name, ','.join(mems)))
                        else:
                            send_msg(s, f'You have already joined Groupchat {group_name}')

                elif command == 'groupmsg':
                    command, group_name, *group_msg = re.split(r'\s', content)
                    group_msg = ' '.join(group_msg)
                    if group_name not in socket_list.keys():
                        send_msg(s, 'The group chat does not exist.')
                    else:
                        if login_user in socket_list[group_name]:
                            for mem in socket_list[group_name]:
                                if mem == login_user:
                                    continue
                                client = socket_list[mem]['socket']
                                send_msg(client, '{}, {}, {}: {}'.format(date, group_name, login_user, group_msg))
                            send_msg(s, 'Group chat message sent at.' + date)
                            LogMsg(lock, login_user, group_msg, '_'.join((group_name, msg_log_file)))
                            print(
                                '>>  {} sent a message in group chat {}:{}; "{}"\n'.format(login_user, group_name, date,
                                                                                       group_msg))

                        else:
                            send_msg(s, 'Please join the group before sending message')
                else:
                    send_msg(s, 'Invalid command!')
    except:
        disconnect(login_user, socket_list, False)


def setupLogs(g_file_name=None):
    if g_file_name:
        f = g_file_name + "_" + msg_log_file
        if os.path.exists(f):
            with open(f, "w") as file:
                pass
        with open(f, 'w') as f:
            pass

    else:
        logs = (msg_log_file, user_log_file)
        for f in logs:
            if os.path.exists(f):
                with open(f, "w") as file:
                    pass
                continue
            with open(f, 'w') as f:
                pass


def LogMsg(lock, user, msg, file_name):
    with lock:
        date = datetime.datetime.now().strftime(DATEFRMT)
        if 'g_' in file_name:
            global g_msg_no
            g_msg_no += 1
            log_msg = (f"{g_msg_no}; {date}; {user}; {msg}")
            with open(file_name, mode='a') as w:
                print(log_msg, file=w)
        elif file_name == msg_log_file:
            global msg_no
            msg_no += 1
            log_msg = (f"{msg_no}; {date}; {user}; {msg}")
            with open(file_name, mode='a') as w:
                print(log_msg, file=w)

        elif file_name == user_log_file:
            global user_no
            user_no += 1
            log_msg = (f"{user_no}; {date}; {user}; {msg}")
            with open(file_name, mode='a') as w:
                print(log_msg, file=w)
            print('>> {} is online\n'.format(user))


def main(server_ip, tcp_port, max_attemps):
    socket_list = {}
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEPORT,
        1)
    s.bind((server_ip, tcp_port))
    s.listen()
    setupLogs()

    lock = threading.Lock()

    while True:
        conn, addr = s.accept()
        threading.Thread(target=socket_target, args=(conn, socket_list, max_attemps, lock)).start()


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python client.py <server_ip> <tcp_port> <max_attemps>")
        sys.exit(1)

    server_ip = sys.argv[1]
    tcp_port = int(sys.argv[2])
    max_attmps = int(sys.argv[3])

    main(server_ip, tcp_port, max_attmps)
