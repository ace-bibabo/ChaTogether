import errno
import random
import socket
import threading
import re
import time
import sys
import os

running = True
auth = False
udp_port = None
server_ip = ''
prompt = '\nEnter one of the following commands (/msgto, /activeuser, /creategroup, /joingroup, /groupmsg, /logout, /p2pvideo):\n'


def UDP_send(receive_addr, filename, sender):
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
            data = "UDP%%" + sender + "_" + filename
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


def UDP_recv():
    server_addr = (server_ip, udp_port)
    try:
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
    except:
        print('udp port already in use!')
        os._exit(0)


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
            if 'Invalid password' not in content:
                print(prompt)
            if 'Welcome' in content:
                auth = True
            elif 'p2pvideo' in content:
                _, addr, receive_port, file_name, sender = re.split(r'\s', content)
                UDP_send((addr, int(receive_port)), file_name, sender)

        except OSError as e:
            print(f"Error reading from server: {e}")
            running = False
            break


def disconnect(s):
    if s:
        s.shutdown(socket.SHUT_RD)
        s.close()


def execute_command(s):
    while running:
        if not auth:
            username = input("Username: ")
            password = input("Password: ")
            if not username.strip() or not password.strip():
                print('Error: close ur connection!')
                disconnect(s)
                break
            s.send(f'{username} {password} {udp_port}'.encode('utf-8'))
        else:
            line = input()
            if not line:
                continue
            pattern = ""
            command = re.split(r'\s', line)[0]
            if 'msgto' == command:
                pattern = r'msgto (\S+) (\S+)'
            elif 'joingroup' == command:
                pattern = r'joingroup (\S+)'
            elif 'creategroup' == command:
                pattern = r'creategroup (\S+) (\S+)'
            elif 'activeuser' == command:
                pattern = r'activeuser'
            elif 'p2pvideo' == command:
                pattern = r'p2pvideo (\S+) (\S+)'
            elif 'groupmsg' == command:
                pattern = r'groupmsg (\S+) (\S+)'

            match = re.search(pattern, line)
            if match:
                send_msg(s, f'{line}')
            else:
                print('Error: Invalid command!')
                print(prompt)
                continue
            if command == 'logout':
                break
        time.sleep(0.1)


def send_msg(s, msg):
    s.send(msg.encode('utf-8'))


def main(server_ip_, tcp_port_, udp_port_):
    global udp_port, server_ip
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    udp_port = udp_port_
    server_ip = server_ip_
    try:
        s.connect((server_ip, tcp_port_))
        print('Please login')
        threading.Thread(target=UDP_recv, args=()).start()
        threading.Thread(target=read_server, args=(s,)).start()

        execute_command(s)
    except:
        print('Connection refused!')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python client.py <server_ip> <tcp_port> <udp_port>")
        sys.exit(1)

    server_ip = sys.argv[1]
    tcp_port = int(sys.argv[2])
    udp_port = int(sys.argv[3])

    main(server_ip, tcp_port, udp_port)
