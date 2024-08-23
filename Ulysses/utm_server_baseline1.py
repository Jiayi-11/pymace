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
import sys
import pickle
import json
import time
import argparse
import threading
import logging
from collections import deque


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
    print("self.timer now is : ",self.timer)
    self.cache = deque([], maxlen=1000)
    
    if self.tag == "uav1":
    #if ((self.tag == "uav1") or (self.tag == "uav2")):
    #if self.timer > self.battery: #Setting the timer to the remaining amount in the battery when the battery is not enough
       self.timer =  900
       print(f"{self.tag}, self.battery is limited: {self.timer}")
    else:
      print(f"{self.tag}, self.battery is perfect: {self.timer}")
    
    
    
    
    
    self._setup()

    try:
        while int(time.time()) < (self.start + self.timer):
            time.sleep(0.001)
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received, exiting UTM Server and saving file.")
        self.save_to_file()
        raise
    else:
        print("Session ended normally")
        self.save_to_file()

    #while int(time.time()) < (self.start + self.timer):
    #  time.sleep(0.001)
    #print("Session ended")
    #self.save_to_file()
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
    self.report_file = open("/home/mace/pymace/reports/wind_farm/results_temp/" + self.tag + ".csv","w")
    #self.report_file.write('time;created;id;aircraft;position;vel;status;inspector_UAV;inspector_UAV_position\n')
    self.report_file.write('time;inspected_WT;inspected_WT_position;inspector_UAV;inspector_UAV_position;distance\n')


    #Ulysses Additions

    self.wt_coordinates = {
        "wt1": (100, 100),  
        "wt2": (700, 100),  
        "wt3": (1300, 100),
        "wt4": (100, 460),
        "wt5": (700, 460),
        "wt6": (1300, 460),
        "wt7": (100, 820),
        "wt8": (700, 820),
        "wt9": (1300, 820)  
    }
     
    self.visited_wt = 0
  
    self.insp_wt=set()
    self.final_missionTime = 100000000000000

    self.flying_distance=0
    self.previous_position=[0,0]
    self.position_skip = False
    self.interval = 0.1
    self.uav_position_tracker = [] #store the positions of the current object (uav) - Ulysses addition
    self.position_file = open("/home/mace/pymace/reports/wind_farm/results_temp/" + self.tag + "position.csv","w") #file to store UAV positions
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


    #self.utm_interface = network_sockets.TcpPersistent(self.utm_packet_handler, debug=False, port=55555, interface='')
    #self.uas_interface = network_sockets.UdpInterface(self.uas_packet_handler, debug=False, port=44444, interface='')
    #self.utm_interface.start()
    #self.uas_interface.start()
   
     #Ulysses adding
    #self.compare_distances()
    self.scheduler.add_job(self.compare_distances, 'interval', seconds = 5, id="compare_distances", args=[])
  




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

        if distance < 65:
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

            #data = json.dumps({
            #                   "created" : created,
            #                   "msg-id" : unique_id,
            #                   "position" : position,
            #                   "velocity" : velocity,
            #                   "status" : status,
            #                   "inspected_WT" : aircraft_id,
            #                   "inspected_WT_position" : (x1, y1), 
            #                   "inspector_UAV" : inspector,
            #                   "inspector_UAV_position" : inspector_position,
            #                   "distance" : distance,
            #})
            #UlyssesAddition

            inspect=False
            self.visited_wt=self.visited_wt+1

            if  self.tag=="uav1":
              if aircraft_id =="wt1" or  aircraft_id =="wt2" or  aircraft_id =="wt3":
                inspect=True   
            elif  self.tag=="uav2":
              if aircraft_id =="wt4" or  aircraft_id =="wt5" or  aircraft_id =="wt6":
                inspect=True
            elif  self.tag=="uav3":
              if aircraft_id =="wt7" or  aircraft_id =="wt8" or  aircraft_id =="wt9":
                inspect=True


            if inspect==True and len(self.insp_wt) <3 and (aircraft_id not in self.insp_wt):
              self.insp_wt.add(aircraft_id)

              self.missionTime=int(time.time()*1000000)

              inspect=True

              data = str(self.missionTime)  + ";" + str(aircraft_id) + ";" + str((x1, y1))+ ";" + str(inspector)+ ";" + str(inspector_position)+ ";" + str(distance) 
              print(inspector, "is inspecting", aircraft_id)
              print(data)

            
              self.save_historic(data)

              if  len(self.insp_wt) == 3 and  self.final_missionTime!=self.missionTime :
                self.final_missionTime= self.missionTime

  #End of Ulysses  
  


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
    if int(time.time()) <= self.final_missionTime:
      self.previous_position=self.get_uav_position()
      #print("The previous position of ",self.tag," is",self.previous_position)

      position = self.gps.get_position()
      position = pickle.loads(position)
      #print("The position got from gps of", self.tag, "is", position)

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
        pos= str(int(time.time()*1000000)) + ';' + str(created)+ ';' + str(identification)+ ';' + str(current_position) + ';' + str(flying_distance) + ';' + str(self.visited_wt)
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
    print("=============The final save method is being executed================")
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

    """
    #try:
    #  payload = pickle.loads(payload)
    #except:
    #  logging.error("UTMServer>utm_packet_handler>Received invalid UDP packet")
#
    #unique_id = payload[0]
    #created = payload[1][0]
    #aircraft_id = payload[1][1]
    #position = payload[1][2]
    #velocity = payload[1][3]
    #status = payload[1][4]
    #inspector_UAV = self.tag
    #inspector_UAV_position = self.get_uav_position()
#
    ##UlyssesAddition
    #inspect=False
#
#
    #if  self.tag=="uav1":
    #  if aircraft_id =="wt1" or  aircraft_id =="wt2" or  aircraft_id =="wt3":
    #    inspect=True
#
#
    #elif  self.tag=="uav2":
    #  if aircraft_id =="wt4" or  aircraft_id =="wt5" or  aircraft_id =="wt6":
    #    inspect=True
    #elif  self.tag=="uav3":
    #  if aircraft_id =="wt7" or  aircraft_id =="wt8" or  aircraft_id =="wt9":
    #    inspect=True
#
    #if inspect==True and len(self.insp_wt) <3 and (aircraft_id not in self.insp_wt):
    #  self.insp_wt.add(aircraft_id)
    # 
    #  self.missionTime=int(time.time()*1000000)
#
    #  inspect=True
    # 
    #  data = str(self.missionTime) + ";" + str(created) + ";" + str(unique_id) + ";" + str(aircraft_id) + ";" + str(position)+ ";" + str(velocity)+ ";" + str(status)+ ";"+str(inspector_UAV) +  ";" + str(inspector_UAV_position)
    #   
    #  self.save_historic(data)
    #  if  len(self.insp_wt) == 3 and  self.final_missionTime!=self.missionTime :
    #    self.final_missionTime= self.missionTime
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
    UTMServer(args.tag, 7200)
  except KeyboardInterrupt:
    logging.info("Exiting UTM Server")



