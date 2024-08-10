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
import subprocess

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
    #self.battery=(random.randint(1,200));#Setting the remaining time in the battery in seconds, the maximum value should be less than timer
    
    if self.tag == "uav0":
    #if ((self.tag == "uav1") or (self.tag == "uav2")):
    #if self.timer > self.battery: #Setting the timer to the remaining amount in the battery when the battery is not enough
       self.timer =  1
       print("this uav is energy limited ")
    else:
      print("the uav has perfect battery ")
    print(self.tag, "self.battery ", self.timer)


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

    #while int(time.time()) < (self.start + self.timer):  #Ulysses Replacement
    # #while (int(time.time()) < (self.start + self.battery)) and  (int(time.time()) < (self.start + self.timer)):
    #  time.sleep(0.001)
    #print("Session ended")

   # self.save_to_file()
   ##self.save_position() #UlyssesAddition




  def _setup(self):
    """ 
    Runs initial configuration

    Parameters
    ----------

    Returns
    --------

    """
    
    self.data_bank_etcd = {}
    self.data_bank = {}

    self.report_file = open("/home/mace/pymace/reports/wind_farm/results_temp/" + self.tag + ".csv", "w")
    #self.report_file.write('time;created;id;aircraft;position;vel;status;inspector_UAV;inspector_UAV_position\n')
    self.report_file.write('time;inspected_WT;inspected_WT_position;inspector_UAV;inspector_UAV_position;distance;status\n')

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
    self.etcd_availability = 0
    self.flying_distance = 0
    self.previous_position = [0,0]
    self.position_skip = False
    self.interval = 0.1
    self.uav_position_tracker = [] #store the positions of the current object (uav) - Ulysses addition
    self.position_file = open("/home/mace/pymace/reports/wind_farm/results_temp/" + self.tag + "position.csv","w") #file to store UAV positions
    self.position_file.write('time;created;uav;uav_position;flying_distance;visited_wt;etcd_availability\n')
    self.scheduler = BackgroundScheduler(timezone=str(tzlocal.get_localzone()))
    logging.getLogger('apscheduler.executors.default').propagate = False
    self.scheduler.start()
    self.scheduler.add_job(self.uav_position_update, 'interval', seconds=self.interval, id="uav_position_update", args=[])
    #self.set_uav_status("OK")
    self.set_uav_position([0,0])
    #self.set_velocity = 0
    self.gps = GPSBridge(self.tag)

    #End of Ulysses


    #try:
    self.etcd = etcd3.client()
    print("Testing etcd object content",self.etcd)

    #Ulysses adding
    self.scheduler.add_job(self.compare_distances, 'interval', seconds=5, id="compare_distances", args=[], max_instances=3)
    self.scheduler.add_job(self.write_to_etcd, 'interval', seconds=8, id="write_to_etcd", args=[], max_instances=3)

    self.etcd.add_watch_callback('wt', self.etcd_callback, range_end='wt999')
    #etcd will watch for the key wt, and when it sees it created, it will run the function self.etcd_callback. 
    
    #except:
    #  logging.info("Running UTM server without etcd")


    
  #Ulysses adding for compare the distance to decide if the UAV is inspecting one WT

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
    inspector = self.tag
    inspector_position = self.get_uav_position()
    x2, y2, _ = inspector_position

    # 存储需要写入的数据
    to_write = []

    for aircraft_id, (x1, y1) in self.wt_coordinates.items():
        distance = self.calculate_distance(x1, y1, x2, y2)
        #print(f"The distance between {self.tag} and wind turbine {aircraft_id} is {distance}m.")

        if distance < 65:
            self.visited_wt = self.visited_wt + 1
            print(self.tag, "Visited wt number is: ", self.visited_wt)

            if aircraft_id not in self.data_bank:
                data = json.dumps({
                                   "inspected_WT" : aircraft_id,
                                   "inspected_WT_position" : (x1, y1), 
                                   "inspector_UAV" : inspector,
                                   "inspector_UAV_position" : inspector_position,
                                   "distance" : distance,
                                   "status": False
                })
                # 将需要写入的数据添加到列表中
                to_write.append((str(aircraft_id), data))
            else:
                print(f"{self.tag}, {aircraft_id} is already inspected, skipping.")
        else:
           pass

    # 对需要写入的数据进行处理
    for aircraft_id, data in to_write:
        #print(inspector, "is trying to inspect", aircraft_id)
        #self.save_to_local_storage(aircraft_id, data)
        #self.write_to_etcd(aircraft_id, data)
        self.data_bank[aircraft_id] = data
        print(f"{self.tag}, Data for {aircraft_id} added to data_bank.")
        
                 
            
  #End of Ulysses  


  def write_to_etcd(self):
    """ 
    Write data to ETCD and count the visited_wt number

    Parameters
    ----------
    aircraft_id (str) - unique aircraft ID
    data (list) - data

    Returns
    --------
    
    """
    
    
    try:    
        # 检查 data_bank_etcd 中是否有未同步到 ETCD 的数据（状态为 False）
        unsynced_data = []
        for key, value in self.data_bank.items():
            data_dict = json.loads(value)
            if data_dict.get("status") == False:
                unsynced_data.append((key, data_dict))


        for key, value in unsynced_data:
            try:  
                # 检查etcd集群的可用性
                status = self.etcd.status()
                if status.leader is not None:
                    self.etcd_availability = self.etcd_availability + 1
                    #print(self.tag, "ETCD is available.")
                    #print(self.tag, "Leader ID:", status.leader)
                    #print(self.tag, "Cluster version:", status.version) #cluster version is always the sam
                    try:
                        if self.etcd.get(key) == (None, None):
                            try:
                                # 更新 data_bank 中的状态为 True
                                data_dict["status"] = True
                                data = json.dumps(data_dict)                           
                        
                                self.etcd.put(key, data)
                                print(self.tag, "ETCD SAVED FOR", key, ":", data)
                                
                            except Exception as e:
                                print(self.tag, "Error while adding data to ETCD:", str(e))
                                # 写入失败时，重新设置状态为 False
                                data_dict["status"] = False
                                # 更新回 data_bank
                                self.data_bank[key] = json.dumps(data_dict)
                                self.etcd_availability = self.etcd_availability - 1
                        else:
                            # 更新 data_bank 中的状态为 True
                            data_dict["status"] = True
                            data = json.dumps(data_dict)
                            #print(self.tag, "The data of this windturbine was already stocked in etcd")
                    except Exception as e:
                        print(self.tag, "Error while searching for key in the ETCD:", str(e))
                        self.etcd_availability = self.etcd_availability - 1
                else:
                    #print(self.tag, "ETCD is not available, trying to save data locally")
                    #self.save_to_local_storage(key, data)
                    pass
            except Exception as e:
                print(self.tag, "UTMServer>write_to_etcd>Error while checking ETCD status:", str(e))

    except Exception as e:
                    print(self.tag, "Error while generating unsynced_data", str(e))

      

  def check_data_bank_completion(self):
    """
    Checks if the data_bank contains all required keys from wt1 to wt9.
    Prints a message once all keys are present.
    """
    required_keys = {f"wt{i}" for i in range(1, 10)}  # 使用集合生成从 wt1 到 wt9 的所有 key
    current_keys = set(self.data_bank_etcd.keys())

    # 检查是否所有必需的 keys 都存在
    if required_keys <= current_keys:
      
        print("==========================================================================================")
        print(self.tag, "finished its mission.")
        print("==========================================================================================")



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
        aircraft_data = aircraft_data.decode()
        #print(self.tag, aircraft_data)

        data_dict = json.loads(aircraft_data)

        #unique_id = data['msg-id']
        aircraft_id = event.key.decode()
        #position = data['position']
        #velocity = data['velocity']
        #status = data['status']
        #created = data['created']
        
        # Check if this data already exists in data_bank_etcd
        if aircraft_id not in self.data_bank_etcd:
            # Extract data from the dictionary and generate a data string only if needed
            inspected_WT_position = data_dict['inspected_WT_position']
            inspector_UAV = data_dict['inspector_UAV']
            inspector_UAV_position = data_dict['inspector_UAV_position']
            inspecting_distance = data_dict['distance']
            #data = str(int(time.time()*1000000)) + ";" + str(created) + ";" + str(unique_id) + ";" + str(aircraft_id) + ";" + str(inspected_WT_position)+ ";" +str(inspector_UAV) + ";" + str(inspector_UAV_position)
            status = data_dict['status']
            data_str = str(int(time.time()*1000000)) + ";" + str(aircraft_id) + ";" + str(inspected_WT_position) + ";" + str(inspector_UAV) + ";" + str(inspector_UAV_position) + ";" + str(inspecting_distance) + ";" + str(status)
            
            self.data_bank_etcd[aircraft_id] = data_str
            print(self.tag, "Data got from etcd is saving: ", data_str)
            
            self.check_data_bank_completion()
            
        # Check if the data needs to be updated in data_bank
        if aircraft_id not in self.data_bank or json.loads(self.data_bank[aircraft_id]).get('status') == False:
            self.data_bank[aircraft_id] = aircraft_data
            print(f"{self.tag} Data for {aircraft_id} added or updated in data_bank.")
        
    except Exception as e:
        #logging.error("UTMServer>etcd_callback>Error getting data from ETCD: " + str(e))
        pass 
  




  def save_historic_etcd(self, aircraft_id, data):
    """ 
    Save updated data from etcd in historic database

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
    self.data_bank_etcd[aircraft_id] = data



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
    if self.previous_position != [0,0]:
      #last_distance_travelled=math.sqrt(((self.previous_position[0]- position[0])**2) + ((self.previous_position[1]- position[1])**2))
      last_distance_travelled = math.sqrt((pow((self.previous_position[0]- position[0]),2))+(pow((self.previous_position[1]- position[1]),2)))
      #print("The last distance travelled ",self.tag," is",last_distance_travelled)
      self.flying_distance += last_distance_travelled
      self.save_position(created, identification, position, self.flying_distance)
     
    

  def save_position(self, created, identification,current_position,flying_distance):#Ulysses Addition
    """ 
    Save positions to file
    --------
    
    """   
    try:
      if not self.position_skip:
        pos= str(int(time.time()*1000000))+';'+ str(created)+';'+str(identification)+';'+str(current_position)+';'+str(flying_distance)+';'+str(self.visited_wt)+';'+str(self.etcd_availability)
        self.uav_position_tracker.append(pos)
     
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
      for data in self.data_bank_etcd.values():
        self.report_file.write(data + '\n')
    except:
      logging.error("UTMServer>save_to_file>Error saving databank to file")

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
      logging.error("UTMServer>save_to_file>Error saving databank to position file")

    
        

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
    UTMServer(args.tag, 8000)

  except KeyboardInterrupt:
    logging.info("Exiting UTM Server")



