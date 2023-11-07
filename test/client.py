import random
import socket
import threading
import re
import time

running = True
auth = False
udp_port = None


def UDP_send(s, receive_addr, filename):
    BUF_SIZE = 1024
    # print(address, port)

    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    count = 0
    f = open(filename, 'rb')
    while True:
        if count == 0:
            print('upp send start 1')
            # send the first message inculding filename
            data = "UDP%%" + str(receive_addr[1]) + "_" + filename
            client.sendto(data.encode('utf-8'), receive_addr)

        data = f.read(BUF_SIZE)
        if str(data) != "b''":
            print('upp send start 2')

            client.sendto(data, receive_addr)
        else:
            print('upp send start 3')

            client.sendto('end'.encode('utf-8'), receive_addr)  # end for the file and send a speical "end" flag
            print(filename + " has been uploaded.")
            execute_command(s)
            break
        count += 1
        time.sleep(0.001)
    f.close()
    client.close()


def UDP_recv():
    while running:
        BUF_SIZE = 1024
        server_addr = ('127.0.0.1', udp_port)

        # UDP: socket.SOCK_DGRAM
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server.bind(server_addr)

        count = 0
        f = None
        filename = ""
        # while running:
        data, addr = server.recvfrom(BUF_SIZE)
        if count == 0:
            # recive the starting message inculding filename
            recv_data_array = data.decode('utf-8').split("%%")
            if len(recv_data_array) > 1:
                if recv_data_array[0] == "UDP":
                    filename = recv_data_array[1]
                    f = open(filename, 'wb')
            count += 1
        elif str(data) != "b'end'":
            try:
                f.write(data)
                # print(count)
            except:
                print("[erroe] can not write")
            count += 1
        else:
            f.close()
            # print(count)
            count = 0
            print("\nReceived " + filename.split("_")[1] + " from " + filename.split("_")[0])


def read_server(s):
    global auth
    while True:
        try:
            content = s.recv(2048).decode('utf-8')
            print('content from server is {}'.format(content))

            if not content or 'Bye' in content or 'blocked' in content or 'error' in content:
                disconnect(s)
                break
            elif 'Welcome' in content:
                auth = True
            elif 'p2p' in content:
                _, addr, receive_port, file_name = re.split(r'\s', content)
                UDP_send(s, (addr, int(receive_port)), file_name)
        except OSError as e:
            print(f"Error reading from server: {e}")
            break


def disconnect(s):
    s.shutdown(socket.SHUT_RD)
    s.close()


def execute_command(s):
    global running, auth
    username = None
    while running:
        if not auth:
            username = input("Username: ")
            password = input("Password: ")
            s.send(f'{username} {password} {udp_port}'.encode('utf-8'))

        else:
            line = input('')
            command = re.split(r'\s', line)[0]
            if command == 'p2p':
                file_name = re.split(r'\s', line)[1]
                receiver = re.split(r'\s', line)[2]
                s.send((f'{command} {username} {file_name} {receiver}').encode('utf-8'))
                continue
            else:
                s.send(line.encode('utf-8'))
                if command == 'exit':
                    running = False
                    break
        time.sleep(0.5)


def main():
    global udp_port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    udp_port = random.randint(13000, 20000)
    s.connect(('127.0.0.1', 12000))

    print('udp port is {}'.format(udp_port))
    threading.Thread(target=UDP_recv, args=()).start()
    threading.Thread(target=read_server, args=(s,)).start()

    execute_command(s)


if __name__ == '__main__':
    main()
