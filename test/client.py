
import random
import socket
import threading
import re


def UDP_send(s, receive_addr, filename):
    address, port = receive_addr
    BUF_SIZE = 1024
    # print(address, port)
    server_addr = (address, int(port))

    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    count = 0
    f = open(filename, 'rb')
    while True:
        if count == 0:
            # send the first message inculding filename
            data = "UDP%%" + 'send_addr' + "_" + filename
            client.sendto(data.encode('utf-8'), server_addr)

        data = f.read(BUF_SIZE)
        if str(data) != "b''":
            client.sendto(data, server_addr)
        else:
            client.sendto('end'.encode('utf-8'), server_addr)  # end for the file and send a speical "end" flag
            print(filename + " has been uploaded.")
            execute_command(s)
            break
        count += 1
        s.sleep(0.001)
    f.close()
    client.close()


def UDP_recv(udp_port):
    BUF_SIZE = 1024
    server_addr = ('127.0.0.1', udp_port)

    # UDP: socket.SOCK_DGRAM
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(server_addr)

    count = 0
    f = None
    filename = ""
    while True:
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
    while True:
        try:
            content = s.recv(2048).decode('utf-8')
            if not content:
                break
            print('content from server is {}'.format(content))
            if 'Bye' in content:
                disconnect(s)
                break

        except OSError as e:
            print(f"Error reading from server: {e}")
            break


def disconnect(s):
    s.shutdown(socket.SHUT_RD)
    s.close()


def execute_command(s):
    while True:
        line = input('')
        if line == 'p2p':
            file_name = re.split(r'\s', line)[1]
            receiver_addr = re.split(r'\s', line)[2]
            UDP_send(s, receiver_addr, file_name)
        else:
            s.send(line.encode('utf-8'))
            if line == 'exit':
                break


def main():
    s = socket.socket()
    s.connect(('127.0.0.1', 12000))
    udp_port = random.randint(20000, 30000)
    # threading.Thread(target=UDP_recv, args=(udp_port,)).start()
    threading.Thread(target=read_server, args=(s,)).start()
    # execute_command(s)


if __name__ == '__main__':
    main()

