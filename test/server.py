import datetime
import re
import socket
import threading
import time

DATEFRMT = '%d %B %Y %H:%M:%S'


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


def disconnect(login_user, socket_list, addr):
    s = socket_list[login_user]['socket']
    send_msg(s, 'Bye, ' + login_user + '!')
    print(login_user + ' logout!')
    socket_list.pop(login_user)

    for g, elem in socket_list.items():
        if type(elem) == list:
            if login_user in elem:
                elem.remove(login_user)
                if not elem or len(elem) == 0:
                    socket_list.pop(g)
                    break

    print('socket_list now is {}'.format(socket_list))


def read_client(s, client_name=None):
    msg = s.recv(2048).decode('utf-8')
    print("server recv {}'s msg: {}".format(client_name, msg))
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
                30.0, block.unblock, args=(user,))
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


def socket_target(s, socket_list, addr, max_attmps):
    failed_attempted = 0
    auth = False
    connected = True
    AUTH_USERS = fetchCredentials()
    login_user = None
    date = datetime.datetime.now().strftime(DATEFRMT)
    blocked = BlockList()

    # try:
    while connected:
        if not auth:
            login_user, pwd, udp_port = re.split(r'\s', read_client(s))

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
                continue

            failed_attempted += 1
            connected, message = checkFailedStatus(failed_attempted, max_attmps, login_user, AUTH_USERS, blocked)
            send_msg(s, message)

        else:
            content = read_client(s, login_user)
            command = re.split(r'\s', content)[0]

            if content is None or 'logout' in content:
                disconnect(login_user, socket_list, addr)
                break
            elif 'p2p' == command:
                command, filename, receiver = re.split(r'\s', content)
                if receiver in socket_list.keys():
                    receive_port = socket_list[receiver]['udp_port']
                    addr = socket_list[receiver]['socket'].getsockname()[0]
                    msg = f'{command} {addr} {receive_port} {filename}'
                    send_msg(s, msg)
                else:
                    s.send((f'receiver not exists').encode('utf-8'))
            elif 'msgto' == command:
                command, receiver, *msg = re.split(r'\s', content)

                if (receiver not in socket_list.keys()) or (
                        receiver in socket_list.keys() and type(socket_list[receiver]) == list):
                    send_msg(s, 'no user exits')
                    continue
                client = socket_list[receiver]['socket']
                send_msg(s, 'message sent at ' + date)
                msg = '{}, {}: {}'.format(date, login_user, ' '.join(msg))
                send_msg(client, msg)
            elif command == 'activeuser':
                activers = []
                for activer, prop in socket_list.items():
                    print(activer)
                    if type(prop) == list:
                        continue
                    addr = prop['socket'].getsockname()[0]
                    login_time = prop['login_time']
                    udp_port = prop['udp_port']
                    activers.append(', '.join([activer, addr, str(udp_port), login_time]))

                msg = '.\n'.join(activers)
                send_msg(s, msg)
            elif command == 'creategroup':
                command, group_name, *mems = re.split(r'\s', content)
                if group_name in socket_list.keys() and type(socket_list[group_name]) == list:
                    send_msg(s, f'Failed to create the group chat {group_name}:group name exists!')
                    continue

                active_mems = []
                for mem in mems:
                    if mem in socket_list.keys():
                        active_mems.append(mem)
                socket_list[group_name] = active_mems
                send_msg(s, f'Group chat created {group_name}')
            elif command == 'joingroup':
                command, group_name = re.split(r'\s', content)
                if group_name not in socket_list.keys():
                    send_msg(s, f'Groupchat {group_name} doesn’t exist.')
                else:
                    if login_user not in socket_list[group_name]:
                        mems = socket_list[group_name]
                        print(mems)
                        mems.append(login_user)
                        socket_list[group_name] = mems
                        send_msg(s, f'Joined the group chat:{group_name} successfully.')
                    else:
                        send_msg(s, f'You have already joined Groupchat {group_name}')
            elif command == 'groupmsg':
                command, group_name, *group_msg = re.split(r'\s', content)
                if group_name not in socket_list.keys():
                    send_msg(s, 'The group chat does not exist.')
                else:
                    if login_user in socket_list[group_name]:
                        for mem in socket_list[group_name]:
                            if mem == login_user:
                                continue
                            client = socket_list[mem]['socket']
                            group_msg = '{}, {}, {}: {}'.format(date, group_name, login_user, ' '.join(group_msg))
                            send_msg(client, group_msg)
                        send_msg(s, 'Group chat message sent at.' + date)
                    else:
                        send_msg(s, 'Please join the group before sending message')
            else:
                send_msg(s, 'Invalid command!')


# except:
#     print('Error!')
#     disconnect(login_user, socket_list, addr)


def main():
    socket_list = {}
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEPORT,
        1)
    s.bind(('127.0.0.1', 12000))
    s.listen()
    max_attps = 3

    while True:
        conn, addr = s.accept()
        print(str(addr) + ' Joined!')
        threading.Thread(target=socket_target, args=(conn, socket_list, addr, max_attps)).start()


if __name__ == '__main__':
    main()
