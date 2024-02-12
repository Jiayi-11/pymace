#!/usr/bin/env python3

""" 
Network class to be used together with UAS/UTM applications
"""
__author__ = "Bruno Chianca Ferreira"
__license__ = "MIT"
__version__ = "0.3"
__maintainer__ = "Bruno Chianca Ferreira"
__email__ = "brunobcf@gmail.com"

import socket, os, math, struct, sys, json, traceback, zlib, fcntl, threading, time, pickle, distutils
from apscheduler.schedulers.background import BackgroundScheduler

class TcpPersistent(threading.Thread):
    def __init__(self, callback, debug=False, port=55123, interface=''):
        threading.Thread.__init__(self)
        self.callback = callback
        self.debug = debug
        self.port = port
        self.interface = interface
        self.running = True
        self.threads = []
        self.max_packet = 65535 #max packet size to listen
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((self.interface, self.port))
            self.server.listen(10000)
        except OSError:
            traceback.print_exc()
            print("Error: unable to open socket on ports '%d' " % (self.port))
            exit(0)

    def stop(self):
        self.running = False
        bye = pickle.dumps(["bye"])
        self.send('127.0.0.1', bye , 255)
        self.server.close()

    def shutdown(self):
        self.stop()

    def __del__(self):
        try:
            self.server.close()
        except:
            pass
    def respond(self, bytes_to_send, msg_id, connection):
        try:
            bytes_to_send = pickle.dumps([hex(msg_id), bytes_to_send])
            length = len(bytes_to_send)
            connection.sendall(struct.pack('!I', length))
            connection.sendall(bytes_to_send)
            connection.close()
        except:
            traceback.print_exc()

    def send(self, destination, bytes_to_send, msg_id, timeout=4):
        """ Send a message over a TCP link"""
        try:
            #print(bytes_to_send)
            bytes_to_send = pickle.dumps([hex(msg_id), bytes_to_send])
            sender_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sender_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sender_socket.settimeout(timeout)
            sender_socket.connect((destination, self.port))
            length = len(bytes_to_send)
            sender_socket.sendall(struct.pack('!I', length))
            sender_socket.sendall(bytes_to_send)
            #sender_socket.send(bytes_to_send)
            lengthbuf = sender_socket.recv(4)
            length, = struct.unpack('!I', lengthbuf)
            response = b''
            while length:
                newbuf = sender_socket.recv(length)
                if not newbuf: return None
                response += newbuf
                length -= len(newbuf)
            #response = sender_socket.recv(self.max_packet)
            sender_socket.close()
            if response == None:
                print("envianto Resposta nula")
            return(response)
        except ConnectionRefusedError:
            bytes_to_send = pickle.dumps(['TIMEOUT'])
            #bytes_to_send = pickle.dumps([hex(0), bytes_to_send])
            return(bytes_to_send)
            if self.debug: print("Could not send data to: " + str(destination))
        except:
            traceback.print_exc()
            if self.debug: print("Could not send data to: " + str(destination))

    def run(self):
        """Thread running function"""
        try:
            while self.running:
                # Parse incoming data
                try:
                    connection, address = self.server.accept()
                    sender_ip = str(address[0])
                    #self.callback(payload, sender_ip, connection)
                    #connection.close()
                    connection_td = threading.Thread(target=self.connection_thread, args=(self.callback, connection, sender_ip))
                    connection_td.start()
                    #self.threads.append(connection_td)
                    continue
                except socket.timeout:
                    #pass
                    traceback.print_exc()
                except:
                    traceback.print_exc()
        except StopIteration:
            traceback.print_exc()

    def connection_thread(self, callback, connection, sender_ip):

        try:
            lengthbuf = connection.recv(4)
            length, = struct.unpack('!I', lengthbuf)
            payload = b''
            while length:
                newbuf = connection.recv(length)
                if not newbuf: return None
                payload += newbuf
                length -= len(newbuf)
            #payload = connection.recv(self.max_packet)
            pickle.loads(payload)
        except:
            traceback.print_exc()
            return
        callback(payload, sender_ip, connection)
        #print(connection)
        #connection.sendall(response)
        #connection.close()

class TcpInterface(threading.Thread):
    def __init__(self, callback, debug=False, port=55123, interface=''):
        threading.Thread.__init__(self)
        self.callback = callback
        self.debug = debug
        self.port = port
        self.interface = interface
        self.running = True
        self.max_packet = 65535 #max packet size to listen
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((self.interface, self.port))
            self.server.listen(10000)
        except OSError:
            print("Error: unable to open socket on ports '%d' " % (self.port))
            exit(0)

    def stop(self):
        try:
            self.server.close()
        except:
            pass

    def send(self, destination, bytes_to_send, msg_id):
        """ Send a message over a TCP link"""
        try:
            bytes_to_send = pickle.dumps([hex(msg_id), bytes_to_send])
            sender_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sender_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sender_socket.settimeout(5)
            sender_socket.connect((destination, self.port))
            length = len(bytes_to_send)
            sender_socket.sendall(struct.pack('!I', length))
            sender_socket.sendall(bytes_to_send)
            sender_socket.close()
        except ConnectionRefusedError:
            #traceback.print_exc()
            if self.debug: print("Could not send data to: " + str(destination))
        except:
            #traceback.print_exc()
            if self.debug: print("Could not send data to: " + str(destination))

    def run(self):
        """Thread running function"""
        try:
            while self.running:
                # Parse incoming data
                try:
                    connection, address = self.server.accept()
                    sender_ip = str(address[0])
                    try:
                        lengthbuf = connection.recv(4)
                        length, = struct.unpack('!I', lengthbuf)
                        payload = b''
                        while length:
                            newbuf = connection.recv(length)
                            if not newbuf: return None
                            payload += newbuf
                            length -= len(newbuf)
                        #payload = connection.recv(self.max_packet) 
                    finally:
                        pass
                except:
                    pass
        except:
            pass

class UdpInterface(threading.Thread):
    """
    UDP Interface class opens a persistent UDP socket and can be used to send data over UDP

    .. note::

       Each instance will be a separate thread with a open socket, thread runs in infinit loop and self.running must be set to False to end the thread.

    """
    def __init__(self, callback, debug=False, port=55123, interface=''):
        """UdpInterface socket class

        Args:
           callback (function): This function will be called when data is received
           debug (bool): When set to true, more information is printed in stdout
           port (int): Integer with port number to be used both to send and received data

        Kwargs:
           interface (str): Interface to where socket will be bind, it not set bind to every interface

        """
        threading.Thread.__init__(self)
        self.callback = callback
        self.debug = debug
        self.port = port
        self.interface = interface
        self.running = True
        self.max_packet = 65535 #max packet size to listen
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.server.bind((self.interface, self.port))
        except OSError:
            print("Error: unable to open socket on ports '%d' " % (self.port))
            exit(0)

    def stop(self):
        """ 
        Stops execution to free the socket

        Parameters
        ----------

        Returns
        --------

        """
        self.running = False
        bye = pickle.dumps('bye'.encode())
        self.send('127.0.0.1', bye, 255)
        self.server.close()

    def shutdown(self):
        """ 
        Shuts down current instance

        Parameters
        ----------

        Returns
        --------

        """
        self.stop()

    def __del__(self):
        try:
            self.server.close()
        except:
            pass

    def send(self, destination, msg_to_send, msg_id):
        """ 
        Send a message over a UDP link. 
        The message is pickled and sent over a UDP socket

        Parameters
        ----------
        destination (str) - IP address of final destination
        msg_to_send (str) - Unpickled message to be sent
        msg_id (binary) - Unique id for the message CRC32

        Returns
        --------

        """
        try:
            bytes_to_send = pickle.dumps([hex(msg_id), msg_to_send])
            sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sender_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sender_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sender_socket.sendto(bytes_to_send,(destination, self.port) )
            #TODO: Keep socket open?
            sender_socket.close()
        except:
            #traceback.print_exc()
            if self.debug: print("Could not send data to: " + str(destination))

    def run(self):
        """ 
        Opens a UDP socket
        When data is received, send to the callback configured during object creation

        Parameters
        ----------

        Returns
        --------

        """
        try:
            while self.running:
                try:
                    payload, address = self.server.recvfrom(self.max_packet)
                    sender_ip = str(address[0])
                    if self.debug: print(payload)
                    self.callback(payload, sender_ip, None)
                except:
                    traceback.print_exc()
                    print("Error receiving UDP data.")
        except StopIteration:
            traceback.print_exc()