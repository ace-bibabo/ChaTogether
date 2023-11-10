import errno
import random
import socket
import threading
import re
import time
import os

running = True
auth = False
udp_port = None
server_ip = ''
prompt = '\nEnter one of the following commands (/msgto, /activeuser, /creategroup,joingroup, /groupmsg, /logout):\n'


def UDP_send(s, receive_addr, filename):
    BUF_SIZE = 1024
    # print(address, port)

    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    count = 0
    if not os.path.exists(filename):
        print(f'No such file or directory: {filename}')
        return
    f = open(filename, 'rb')
    while True:
        if count == 0:
            data = "UDP%%" + str(receive_addr[1]) + "_" + filename
            client.sendto(data.encode('utf-8'), receive_addr)

        data = f.read(BUF_SIZE)
        if str(data) != "b''":
            client.sendto(data, receive_addr)
        else:
            client.sendto('end'.encode('utf-8'), receive_addr)  # end for the file and send a speical "end" flag
            print(filename + " has been uploaded.")
            break
    f.close()
    client.close()
    time.sleep(0.1)


def UDP_recv(s):
    server_addr = (server_ip, udp_port)

    # UDP: socket.SOCK_DGRAM
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(server_addr)
    server.setblocking(False)
    count = 0
    f = None
    filename = ""
    while running:
        try:
            data, addr = server.recvfrom(1024)
            if count == 0:
                count += 1
                recv_data_array = data.decode('utf-8').split("%%")
                if len(recv_data_array) > 1:
                    udp_type, filename = recv_data_array

                    if udp_type == "UDP":
                        f = open(filename, 'wb')
            elif str(data) != "b'end'":
                count += 1
                f.write(data)
            else:
                f.close()
                count = 0
                print("\nReceived " + filename.split("_")[1] + " from " + filename.split("_")[0])
                # execute_command(s)
        except socket.error as e:
            if e.errno == errno.EWOULDBLOCK:
                pass
            else:
                print(":", e)


def read_server(s):
    global running, auth
    while running:
        try:
            content = s.recv(2048).decode('utf-8')
            print(content)
            if not content or 'Bye' in content or 'blocked' in content or 'error' in content:
                disconnect(s)
                running = False
                break
            print(prompt)
            if 'Welcome' in content:
                auth = True
            elif 'p2p' in content:
                _, addr, receive_port, file_name = re.split(r'\s', content)
                UDP_send(s, (addr, int(receive_port)), file_name)
        except OSError as e:
            print(f"Error reading from server: {e}")
            running = False
            break


def disconnect(s):
    s.shutdown(socket.SHUT_RD)
    s.close()


def execute_command(s):
    while running:
        if not auth:
            username = input("Username: ")
            password = input("Password: ")
            s.send(f'{username} {password} {udp_port}'.encode('utf-8'))
        else:
            line = input()
            if not line:
                continue
            command = re.split(r'\s', line)[0]
            send_msg(s, f'{line}')
            if command == 'logout':
                break
        time.sleep(0.1)


def send_msg(s, msg):
    s.send(msg.encode('utf-8'))


def main():
    global udp_port, server_ip
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    udp_port = random.randint(13000, 20000)
    server_ip = '127.0.0.1'
    s.connect((server_ip, 12000))

    print('Please login')
    threading.Thread(target=UDP_recv, args=(s,)).start()
    threading.Thread(target=read_server, args=(s,)).start()

    execute_command(s)


if __name__ == '__main__':
    main()
