#!/usr/bin/env python3

""" 
Network class is part of a thesis work about distributed systems 
"""
__author__ = "Bruno Chianca Ferreira"
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Bruno Chianca Ferreira"
__email__ = "brunobcf@gmail.com"

# Python stdlib
import math
from os import execl
import random
import sys
import pickle
import json
import time
import argparse
import threading
import logging
from collections import deque
#etcd

import etcd3

#local
import network_sockets

#Ulysses imports
import tzlocal
from apscheduler.schedulers.background import BackgroundScheduler
from gps_bridge import GPSBridge

class UTMServer():
  """
  Emulates a simple implementation of the UAS endpoint on a UTM data service provider

  .. note::

      Each instance will be a separate thread with a open socket, thread runs in infinit loop and self.running must be set to False to end the thread.

  """
  Inspected_windTurbines= {} #to store the windturbines ids that were inspected i.e. its data was collected
  

  
  def __init__(self, tag, timer):
    """UTMServer UAS endpoint

    Args:
        tag (str) - A unique identifier for the UTM server
        timer (int) - For how long the session should run in seconds

    Kwargs:
        

    """
    self.tag = tag
  
    self.start = int(time.time())
    self.timer = timer
    print("self.timer ",self.timer)
    self.cache = deque([], maxlen=1000)
    #self.battery=(random.randint(1,200));#Setting the remaining time in the battery in seconds, the maximum value should be less than timer
    
    if self.tag == "uav0":
    #if ((self.tag == "uav1") or (self.tag == "uav2")):
    #if self.timer > self.battery: #Setting the timer to the remaining amount in the battery when the battery is not enough
       self.timer =  1
       print("this uav is energy limited ")
    else:
      print("the uav has perfect battery ")
    print(self.tag, "self.battery ", self.timer)
   
    #print(self.calculate_distance(0, 0, 1, 2))

    self._setup()
    while int(time.time()) < (self.start + self.timer):  #Ulysses Replacement
     #while (int(time.time()) < (self.start + self.battery)) and  (int(time.time()) < (self.start + self.timer)):
      time.sleep(0.001)
    print("Session ended")
     
    
    self.save_to_file()
   #self.save_position() #UlyssesAddition

  def _setup(self):
    """ 
    Runs initial configuration

    Parameters
    ----------

    Returns
    --------

    """
    
    self.data_bank = []
    self.report_file = open("/home/mace/pymace/reports/wind_farm/" + self.tag + ".csv","w")
    #self.report_file.write('time;created;id;aircraft;position;vel;status;inspector_UAV;inspector_UAV_position\n')
    self.report_file.write('time;inspected_WT;inspected_WT_position;inspector_UAV;inspector_UAV_position;distance\n')

    #Ulysses Additions
    #self.coordinates_wt = [(0, 0), (770, 0), (1540, 0), (0, 770), (770, 770), (1540, 770), (0, 1540), (770, 1540), (1540, 1540)]
    self.wt_coordinates = {
        "wt1": (500, 500),  
        "wt2": (1500, 500),  
        "wt3": (2500, 500),
        "wt4": (500, 1100),
        "wt5": (1500, 1100),
        "wt6": (2500, 1100),
        "wt7": (500, 1700),
        "wt8": (1500, 1700),
        "wt9": (2500, 1700)  
    }


    self.visited_wt=0
    self.flying_distance=0
    self.previous_position=[0,0]
    self.position_skip = False
    self.interval = 0.1
    self.uav_position_tracker = [] #store the positions of the current object (uav) - Ulysses addition
    self.position_file = open("/home/mace/pymace/reports/wind_farm/" + self.tag + "position.csv","w") #file to store UAV positions
    self.position_file.write('time;created;uav;uav_position;flying_distance;visited_wt\n')
    self.scheduler = BackgroundScheduler(timezone=str(tzlocal.get_localzone()))
    logging.getLogger('apscheduler.executors.default').propagate = False
    self.scheduler.start()
    self.scheduler.add_job(self.uav_position_update, 'interval', seconds = self.interval, id="uav_position_update", args=[])
    #self.set_uav_status("OK")
    self.set_uav_position([0,0])
    #self.set_velocity = 0
    self.gps = GPSBridge(self.tag)

    #End of Ulysses


    self.utm_interface = network_sockets.TcpPersistent(self.utm_packet_handler, debug=False, port=55555, interface='')
    self.uas_interface = network_sockets.UdpInterface(self.uas_packet_handler, debug=False, port=44444, interface='')
    self.utm_interface.start()
    self.uas_interface.start()
    #try:
    self.etcd = etcd3.client()
    print("Testing etcd object content",self.etcd)

    #Ulysses adding
    #self.compare_distances()
    self.scheduler.add_job(self.compare_distances, 'interval', seconds = 5, id="compare_distances", args=[])

    self.etcd.add_watch_callback('wt', self.etcd_callback, range_end='wt999')
    #except:
    #  logging.info("Running UTM server without etcd")

    


  #Ulysses adding
  def calculate_distance(self, x1, y1, x2, y2):
    """
    Calculate the Euclidean distance between two points
    """
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)



  def compare_distances(self):
    """
    Compare the distance of coordinates_uav to a series of coordinates_wt.
    If the distance is less than 5, print the message.
    
    """
    #x1, y1 = coordinates_wt
    coordinates_uav = self.get_uav_position()
    #print("the coordinates of", self.tag, "is", coordinates_uav)
    x2, y2, _ = coordinates_uav

    for aircraft_id, (x1, y1) in self.wt_coordinates.items():
        distance = self.calculate_distance(x1, y1, x2, y2)
        #print(f"The distance between {self.tag} and wind turbine {aircraft_id} is {distance}m.")

        if distance < 80:
            #print(f"The distance between {self.tag} and wind turbine {aircraft_id} is less than 500m.")
            #try:
            #  payload = pickle.loads(payload)
            #except:
            #  logging.error("UTMServer>utm_packet_handler>Received invalid UDP packet")

            #unique_id = payload[0]

            #created = payload[1][0]
            #aircraft_id = payload[1][1]
            #position = payload[1][2]
            #velocity = payload[1][3]
            #status = payload[1][4]
            inspector = self.tag
            inspector_position = self.get_uav_position()

            data = json.dumps({
            #                   "created" : created,
            #                   "msg-id" : unique_id,
            #                   "position" : position,
            #                   "velocity" : velocity,
            #                   "status" : status,
                               "inspected_WT" : aircraft_id,
                               "inspected_WT_position" : (x1, y1), 
                               "inspector_UAV" : inspector,
                               "inspector_UAV_position" : inspector_position,
                               "distance" : distance,
            })
            
            self.write_to_etcd(aircraft_id, data)
            #print("write_to_etcd is called")

  #End of Ulysses  



  def etcd_callback(self, _event):
    """ 
    Callback function called everytime etcd senses data change in configure key

    Parameters
    ----------
    _event (list) - ETCD event list

    Returns
    --------

    """
    try:
      for event in _event.events:
        aircraft_data, _ = self.etcd.get(event.key)
        aircraft_data.decode()

        data = json.loads(aircraft_data)

        #unique_id = data['msg-id']
        aircraft_id = event.key.decode()
        #position = data['position']
        #velocity = data['velocity']
        #status = data['status']
        #created = data['created']
        
        inspected_WT_position = data['inspected_WT_position']
        inspector_UAV = data['inspector_UAV']
        inspector_UAV_position = data['inspector_UAV_position']
        distance = data['distance']
        #data = str(int(time.time()*1000000)) + ";" + str(created) + ";" + str(unique_id) + ";" + str(aircraft_id) + ";" + str(inspected_WT_position)+ ";" +str(inspector_UAV) + ";" + str(inspector_UAV_position)
        data = str(int(time.time()*1000000)) + ";" + str(aircraft_id) + ";" + str(inspected_WT_position)+ ";" +str(inspector_UAV) + ";" + str(inspector_UAV_position) + ";" + str(distance)
        #print("Data got from etcd is saving: ", data)

        self.save_historic(data)
    except:
      logging.error("UTMServer>etcd_callback>Error getting data from ETCD")

  def save_historic(self, data):
    """ 
    Save updated aircraft data in historic database

    Parameters
    ----------
    data (list) - aircraft data
      current_time - Current time when saving
      created_time - Time data was created
      unique_id - Unique message id on creation
      aircraft_id - Aircraft id
      position - Current aircraft position
      velocity - Current aircraft velocity
      status - Current aircraft status

    Returns
    --------

    """    
    self.data_bank.append(data)


  def callback_thread(self, event):
    """ 
    Deprecated

    """    
    try:
      aircraft_data, _ = self.etcd.get(event.key)
    except:
      pass
    aircraft_data.decode()
    data = json.loads(aircraft_data)
    unique_id = data['msg-id']
    aircraft_id = event.key.decode()
    position = data['position']
    velocity = data['velocity']
    status = data['status']
    created = data['created']
    #inspector_UAV= data['inspector_UAV']
    data = str(int(time.time()*1000000)) + ";" + str(created) + ";" + str(unique_id) + ";" + str(aircraft_id) + ";" + str(position)+ ";" + str(velocity)+ ";" + str(status)
    self.data_bank.append(data)

  def set_uav_status(self, status):#Added for Ulysses 
    """ 
    Sets the status

    Parameters
    ----------
    status (string) - Current status
    TODO:create ENUM of valid statuses

    Returns
    --------
    

    """     
    self.status = status
  
  def set_uav_position(self, pos):
    """ 
    Set the position

    Parameters
    ----------
    pos (list) - Coordinates X, Y

    Returns
    --------

    """
    self.surface_position = pos

  def uav_position_update(self): #Ulysses Addition
    """ 
    Broadcasts UAS information.
    Pools the position from the GPS and calls broadcast

    Parameters
    ----------

    Returns
    --------

    """
    self.previous_position=self.get_uav_position()
    #print("The previous position of ",self.tag," is",self.previous_position)

    position = self.gps.get_position()
    position = pickle.loads(position)

    if position == [-1, -1, -1]:
      self.set_uav_position([100,100])
    else:
      self.set_uav_position(position)

    created = str(int(time.time()*1000000))
    #print("the creation time is ", time.time())
    identification = self.tag
    position = self.get_uav_position()
    
    #print("The current position of ",self.tag," is",position)
    if self.previous_position!=[0,0]:
      #last_distance_travelled=math.sqrt(((self.previous_position[0]- position[0])**2) + ((self.previous_position[1]- position[1])**2))
      last_distance_travelled=math.sqrt((pow((self.previous_position[0]- position[0]),2))+(pow((self.previous_position[1]- position[1]),2)))
      #print("The last distance travelled ",self.tag," is",last_distance_travelled)
      self.flying_distance+=last_distance_travelled
      #print("The total flying distance ",self.tag," is",self.flying_distance)
      self.save_position(created, identification,position,self.flying_distance)
     
    

  def save_position(self, created, identification,current_position,flying_distance):#Ulysses Addition
    """ 
    Save positions to file
    --------
    
    """   
    try:
      if not self.position_skip:
        pos= str(int(time.time()*1000000)) + ';' + str(created)+ ';' + str(identification)+ ';'  + str(current_position)  + ';' + str(flying_distance)+ ';'+str(self.visited_wt)
        self.uav_position_tracker.append(pos)
        #self.position_file.write()
        
        #if not self.position_skip:
          #logging.info("UAV_server>save_to_file>Emulation session ended. Saving to positions file")
      #else:
          #self.position_file.flush()
          #self.position_file.close()
          #self.position_skip = True
    except:
      pass

  def get_uav_position(self): #Added for Ulysses 
    """ 
    Returns the current position

    Parameters
    ----------

    Returns
    --------
    pos (list) - Coordinates X, Y

    """
    return self.surface_position
  
  def get_uav_status(self):
    """ 
    Gets the current status

    Parameters
    ----------


    Returns
    --------
    status (string) - Current status
    
    """     
    return self.status
  
  def save_to_file(self):
    """ 
    Save databank to file

    Parameters
    ----------

    Returns
    --------
    
    """
    try: 
      for data in self.data_bank:
        self.report_file.write(data + '\n')
    except:
      logging.error("UTMServer>save_to_file>Error saving databack to file")

    self.report_file.flush()
    self.report_file.close()

    try: 
      #self.position_file.flush()
      #self.position_file.close()
      for uav_position in self.uav_position_tracker:
        self.position_file.write(uav_position + '\n')
      self.position_file.flush()
      self.position_file.close()
      self.etcd.close()
    except:
      logging.error("UTMServer>save_to_file>Error saving databack to position file")

    
        

  def utm_packet_handler(self, payload, sender_ip, connection):
    """ 
    UTM packet handler
    Called when data arrives on UTM endpoint

    Parameters
    ----------
    payload (bin) - Pickled payload
    sender_ip (str) - Sender's IP address 
    connection (socket) - Connection open socket

    Returns
    --------

    """
    pass



  def uas_packet_handler(self, payload, sender_ip, connection):

    """
    UAS packet handler
    Called when data arrives on UAS endpoint

    Parameters
    ----------
    payload (bin) - Pickled payload
    sender_ip (str) - Sender's IP address 
    connection (socket) - Connection open socket

    Returns
    --------
    
    
    try:
      payload = pickle.loads(payload)
    except:
      logging.error("UTMServer>utm_packet_handler>Received invalid UDP packet")

    unique_id = payload[0]

    created = payload[1][0]
    aircraft_id = payload[1][1]
    position = payload[1][2]
    velocity = payload[1][3]
    status = payload[1][4]
    inspector = self.tag
    inspector_position = self.get_uav_position()

    data = json.dumps({"created" : created,
                       "msg-id" : unique_id,
                       "position" : position,
                       "velocity" : velocity,
                       "status" : status,
                       "inspector_UAV" : inspector,
                       "inspector_UAV_position" : inspector_position,
    })
    #wt_found=False
    #for wt in UTMServer.Inspected_windTurbines:
      #if wt==aircraft_id:
        #wt_found=True
        #break

    #if (UTMServer.Inspected_windTurbines.get(aircraft_id)==None): #added by us 
    #if wt_found==False:
      #UTMServer.Inspected_windTurbines[aircraft_id]= self.tag
      #print("This is the list of read windturbines: ",UTMServer.Inspected_windTurbines)
    self.write_to_etcd(aircraft_id, data)
    """ 
    pass



  def write_to_etcd(self, aircraft_id, data):
    """ 
    Write data to ETCD

    Parameters
    ----------
    aircraft_id (str) - unique aircraft ID
    data (list) - data

    Returns
    --------
    
    """
    #print("The length of get all is ",  len(list(self.etcd.get_all())) )
    try:
     self.visited_wt=self.visited_wt+1
     #if !(self.tag="uav1" and int(time.time()*1000000)>2):
     if self.etcd.get(aircraft_id)==(None,None):
       try:
           print("We are trying to write", aircraft_id, "to ETCD" )
      
           #data+= ";" + str(self.tag)
           print(data)
           #data=data+";" + str(self.tag)
           #print(data)
           self.etcd.put(aircraft_id, data)
          
           #if( len(list(self.etcd.get_all()))==9):
             #position_skip=True
           


             #self.start=0
             #self.timer=0
             #print("Session ended")
             #self.save_to_file()



       except:
        print("Error while adding data to ETCD")
        pass
     else: 
      print("The data of this windturbine was already collected")
      pass
        
    except:
        print("Error while searching for key in the ETCD")
        pass

#######################Class END###############################################################################################




def parse_args():
  """ 
  Method for parsing command line arguments

  Parameters
  ----------

  Returns
  --------
  args - Arguments

  """
  parser = argparse.ArgumentParser(description='Some arguments are obligatory and must follow the correct order as indicated')
  parser.add_argument("-t", "--tag", help="Tag name", type=str)
  return parser.parse_args()

def set_logging():
  """ 
  Sets the logging levels

  Parameters
  ----------

  Returns
  --------

  """
  logging.Formatter('%(asctime)s -> [%(levelname)s] %(message)s')
  logger = logging.getLogger()
  logger.setLevel(logging.INFO)
  logging.basicConfig(level='INFO')

###########################Runner ################################################################################################


if __name__ == '__main__':
  set_logging()
  logging.info("Starting UTM server")
  args = parse_args()
  try:
    
    UTMServer(args.tag, 100)

  except KeyboardInterrupt:
    logging.info("Exiting UTM Server")



