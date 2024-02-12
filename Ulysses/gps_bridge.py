import traceback, socket, pickle, struct, logging


class GPSBridge:

  def __init__(self, tag) -> None:
    self.position = []
    self.tag = tag
    self._setup()

  def _setup(self):
    pass

  def poll_gps(self):
    pass

  def get_position(self):
    data = [self.tag, 'GET_POSITION']
    gps = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    gps.settimeout(1)
    try: 
      gps.connect("/tmp/" + self.tag +"_gps.sock")
    except FileNotFoundError:
      print("GPS " + "/tmp/" + self.tag +"_gps.sock" +  " not found. Check tag or emulator")
      payload = pickle.dumps([-1, -1, -1])
      return payload
    except:
      print("/tmp/" + self.tag +"_gps.sock")
      traceback.print_exc()
    payload = pickle.dumps(data)
    length = len(payload)
    try:
      gps.sendall(struct.pack('!I', length))
      gps.sendall(payload)
      lengthbuf = gps.recv(4)
      length, = struct.unpack('!I', lengthbuf)
      data = b''
      while length:
        newbuf = gps.recv(length)
        if not newbuf: return None
        data += newbuf
        length -= len(newbuf)
    except:
      logging.error("Could not send data.")
    gps.close()
    return data