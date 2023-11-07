import socket
import threading


def disconnect(s, socket_list, addr):
    s.send(('Bye ' + str(addr)).encode('utf-8'))

    print(str(addr) + ' Left!')
    socket_list.remove(s)



def read_client(s, socket_list, addr):
    try:
        return s.recv(2048).decode('utf-8')
    except:
        disconnect(s, socket_list, addr)


def socket_target(s, socket_list, addr):
    try:
        while True:
            content = read_client(s, socket_list, addr)
            print("content from client is {}".format(content))
            if content is None or 'exit' in content:
                disconnect(s, socket_list, addr)
                break
            else:
                print(content)
            for client in socket_list:
                client.send((str(addr) + ' say: ' + content).encode('utf-8'))
    except:
        print('Error!')
        disconnect(s, socket_list, addr)


def main():
    socket_list = []
    s = socket.socket()
    s.bind(('127.0.0.1', 12000))
    s.listen()

    while True:
        conn, addr = s.accept()
        socket_list.append(conn)
        print(str(addr) + ' Joined!')
        threading.Thread(target=socket_target, args=(conn, socket_list, addr)).start()


if __name__ == '__main__':
    main()
