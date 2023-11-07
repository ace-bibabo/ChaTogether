import random
import socket
import threading
import re
import time

running = True
running_lock = threading.Lock()


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


def UDP_recv(udp_port):
    print("TCP_running in UDP_recv is {}".format(running))

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
    while True:
        try:
            content = s.recv(2048).decode('utf-8')
            print('content from server is {}'.format(content))

            if not content or 'Bye' in content:
                disconnect(s)
                break

        except OSError as e:
            print(f"Error reading from server: {e}")
            break


def disconnect(s):
    s.shutdown(socket.SHUT_RD)
    s.close()


def execute_command(s):
    global running
    while running:
        line = input('')
        command = re.split(r'\s', line)[0]
        if command == 'p2p':
            file_name = re.split(r'\s', line)[1]
            receiver_ip = re.split(r'\s', line)[2]
            receiver_port = re.split(r'\s', line)[3]
            UDP_send(s, (receiver_ip, int(receiver_port)), file_name)
        else:
            s.send(line.encode('utf-8'))
            if command == 'exit':
                with running_lock:
                    running = False
                    print("TCP_running in execute_command is {}".format(running))
                    break


def main():
    s = socket.socket()
    s.connect(('127.0.0.1', 12000))
    udp_port = random.randint(13000, 20000)
    print('udp port is {}'.format(udp_port))
    threading.Thread(target=UDP_recv, args=(udp_port,)).start()
    threading.Thread(target=read_server, args=(s,)).start()

    execute_command(s)


if __name__ == '__main__':
    main()
