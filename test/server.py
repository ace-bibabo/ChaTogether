import re
import socket
import threading


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
    s.send(('Bye ' + str(addr)).encode('utf-8'))
    print(str(addr) + ' Left!')
    socket_list.pop(login_user)


def read_client(s, client_name=None):
    msg = s.recv(2048).decode('utf-8')
    print("server recv {}'s msg: {}".format(client_name, msg))
    return msg


def socket_target(s, socket_list, addr):
    failed_attempted = 0
    auth = False
    connected = True
    AUTH_USERS = fetchCredentials()
    login_user = None

    try:
        while connected:
            if not auth:
                login_user, pwd, udp_port = re.split(r'\s', read_client(s))
                verified = authenticateUser(AUTH_USERS, login_user, pwd)

                if verified:
                    auth = True
                    socket_list[login_user] = {'socket': s, 'udp_port': udp_port}
                    s.send(('Welcome!').encode('utf-8'))
                    continue
                else:
                    failed_attempted += 1

            else:
                content = read_client(s, login_user)

                if content is None or 'exit' in content:
                    disconnect(login_user, socket_list, addr)
                    break
                elif 'p2p' in content:
                    print("p2p is coming")
                    print("haha is coming {}".format(re.split(r'\s', content)))
                    command, sender, filename, receiver = re.split(r'\s', content)
                    print("server receive p2p from {} to {} transfer {}".format(sender, receiver, filename))

                    if receiver in socket_list.keys():
                        receive_port = socket_list[receiver]['udp_port']
                        addr = socket_list[receiver]['socket'].getsockname()[0]
                        s.send((f'{command} {addr} {receive_port} {filename}').encode('utf-8'))
                    else:
                        s.send((f'receiver not exists').encode('utf-8'))
                    continue
                for receive_user, v in socket_list.items():
                    if receive_user != login_user:
                        client = v['socket']
                        client.send((login_user + ' say: ' + content).encode('utf-8'))
    except:
        print('Error!')
        disconnect(login_user, socket_list, addr)


def main():
    socket_list = {}
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEPORT,
        1)
    s.bind(('127.0.0.1', 12000))
    s.listen()

    while True:
        conn, addr = s.accept()
        print(str(addr) + ' Joined!')
        threading.Thread(target=socket_target, args=(conn, socket_list, addr)).start()


if __name__ == '__main__':
    main()
