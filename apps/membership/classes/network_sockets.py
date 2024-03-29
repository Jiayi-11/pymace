#!/usr/bin/env python3

""" 
Network class is part of a thesis work about distributed systems 
"""
__author__ = "Bruno Chianca Ferreira"
__license__ = "MIT"
__version__ = "0.3"
__maintainer__ = "Bruno Chianca Ferreira"
__email__ = "brunobcf@gmail.com"

import socket, os, math, struct, sys, json, traceback, zlib, fcntl, threading, time, pickle, distutils

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

  def send(self, destination, bytes_to_send, msg_id, timeout=0.5):
    """ Send a message over a TCP link"""
    try:
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
      #traceback.print_exc()
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
    self.running = False
    bye = pickle.dumps('bye'.encode())
    self.send('127.0.0.1', bye, 255)
    #self.sender_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #self.sender_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #self.sender_socket.connect(('127.0.0.1', self.port))
    #self.sender_socket.sendall(bye)
    #self.sender_socket.close()
    self.server.close()

  def shutdown(self):
    self.stop()

  def __del__(self):
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
      sender_socket.settimeout(0.5)
      sender_socket.connect((destination, self.port))
      length = len(bytes_to_send)
      sender_socket.sendall(struct.pack('!I', length))
      sender_socket.sendall(bytes_to_send)
      #sender_socket.send(bytes_to_send)
      #lengthbuf = sender_socket.recv(4)
      #length, = struct.unpack('!I', lengthbuf)
      #response = b''
      #while length:
      #    newbuf = sender_socket.recv(length)
      #    if not newbuf: return None
      #    response += newbuf
      #    length -= len(newbuf)
      sender_socket.close()
      #return(response)
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
            connection.close()
            self.callback(payload, sender_ip, None)
        except socket.timeout:
          print("error receiving, timeout")
          pass
          #traceback.print_exc()
        except:
          print("error receiving")
          pass

    except StopIteration:
      traceback.print_exc()
      #pass

class UdpInterface(threading.Thread):
  """_summary_

  Args:
      threading (_type_): _description_
  """
  def __init__(self, callback, debug=False, port=55123, interface=''):
    """_summary_

    Args:
        callback (function): _description_
        debug (bool, optional): _description_. Defaults to False.
        port (int, optional): _description_. Defaults to 55123.
        interface (str, optional): _description_. Defaults to ''.
    """
    threading.Thread.__init__(self)
    self.settings = _setup()
    self.callback = callback
    self.debug = debug
    self.port = port
    self.interface = interface
    self.running = True
    self.max_packet = 65536 #max packet size to listen
    try:
      self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      self.server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
      self.server.bind((self.interface, self.port))
    except OSError:
      print("Error: unable to open socket on ports '%d' " % (self.port))
      exit(0)

  def stop(self):
    """_summary_
    """
    self.running = False
    #bye = pickle.dumps('bye'.encode())
    self.send('127.0.0.1', "bye")
    self.server.close()

  def shutdown(self):
    """_summary_
    """
    self.stop()

  def __del__(self):
    """_summary_
    """
    try:
      self.server.close()
    except:
      pass

  def broadcast(self, payload):
    self.send(self.settings["bcast_group"], payload)

  def send(self, destination, payload):
    """Sends a message via UDP

    Args:
        destination (_type_): _description_
        payload (_type_): _description_
        msg_id (_type_): _description_

    Returns:
        _type_: _description_
    """
    try:
      bytes_to_send = pickle.dumps(payload)
      sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      sender_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      sender_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
      r = sender_socket.sendto(bytes_to_send,(destination, self.port) )
      #TODO: Keep socket open?
      sender_socket.close()
      return r
    except:
      traceback.print_exc()
      if self.debug: print("Could not send data to: " + str(destination))

  def run(self):
    """_summary_
    """
    try:
      while self.running:
        # Parse incoming data
        try:
          payload, address = self.server.recvfrom(self.max_packet)
          sender_ip = str(address[0])
          if self.debug: print(payload)
          self.callback(payload, sender_ip)
        except:
          traceback.print_exc()
          print("Error receiving UDP data.")
    except StopIteration:
      traceback.print_exc()

class Network():

  def __init__(self, node, settings):
    'Initializes the properties of the Node object'
    #### NODE ###############################################################################
    self.node = node
    self.tagnumber = node
    #### NETWORK ##############################################################################
    self.ip = settings["ip"] 
    self.port = settings["port"] # UDP port 
    self.max_packet = 1500 #max packet size to listen
    #### UTILITIES ############################################################################
    self.stats = [0,0,0,0] #created, forwarded, delivered, discarded
    self.errors = [0,0,0]
    ##################### END OF DEFAULT SETTINGS ###########################################################
    self._setup()

  ############### Public methods ###########################

  def start(self):
    pass

  def shutdown(self):
    pass


def _setup():
  settings_file = open("./classes/network_settings.json","r").read()
  settings = json.loads(settings_file)
  interface_stem = settings['interface']
  if interface_stem == "tap":
    interface = interface_stem + str(self.tagnumber)
  else:
    interface = interface_stem + '0'
  port = settings['networkPort']
  bcast_group = settings['ipv4bcast']
  settings = {
    "interface" :interface,
    "port": port,
    "bcast_group": bcast_group,
    "version": 4
  }
  return settings

def _get_ip(iface = 'eth0'):
  'Gets IP address'
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sockfd = sock.fileno()
  SIOCGIFADDR = 0x8915
  ifreq = struct.pack('16sH14s', iface.encode('utf-8'), socket.AF_INET, b'\x00'*14)
  try:
    res = fcntl.ioctl(sockfd, SIOCGIFADDR, ifreq)
  except:
    traceback.print_exc()
    return None
  ip = struct.unpack('16sH2x4s8x', res)[2]
  return socket.inet_ntoa(ip)