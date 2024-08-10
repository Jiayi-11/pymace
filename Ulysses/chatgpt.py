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
import random
import sys
import pickle
import json
import time
import argparse
import threading
import logging
from collections import deque
import etcd3
import network_sockets
import tzlocal
from apscheduler.schedulers.background import BackgroundScheduler
from gps_bridge import GPSBridge
import subprocess

class UTMServer():
    """
    Emulates a simple implementation of the UAS endpoint on a UTM data service provider

    .. note::

        Each instance will be a separate thread with an open socket, thread runs in an infinite loop and self.running must be set to False to end the thread.

    """
    Inspected_windTurbines = {}  # to store the windturbines ids that were inspected i.e. its data was collected

    def __init__(self, tag, timer):
        self.tag = tag
        self.start = int(time.time())
        self.timer = timer
        print("self.timer now is : ", self.timer)
        self.cache = deque([], maxlen=1000)

        if self.tag == "uav0":
            self.timer = 1
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

    def _setup(self):
        self.data_bank_etcd = {}
        self.data_bank_local = {}

        self.report_file = open("/home/mace/pymace/reports/wind_farm/results_temp/" + self.tag + ".csv", "w")
        self.report_file.write('time;inspected_WT;inspected_WT_position;inspector_UAV;inspector_UAV_position;distance;data_source\n')

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
        self.flying_distance = 0
        self.previous_position = [0, 0]
        self.position_skip = False
        self.interval = 0.1
        self.uav_position_tracker = []
        self.position_file = open("/home/mace/pymace/reports/wind_farm/results_temp/" + self.tag + "position.csv", "w")
        self.position_file.write('time;created;uav;uav_position;flying_distance;visited_wt\n')
        self.scheduler = BackgroundScheduler(timezone=str(tzlocal.get_localzone()))
        logging.getLogger('apscheduler.executors.default').propagate = False
        self.scheduler.start()
        self.scheduler.add_job(self.uav_position_update, 'interval', seconds=self.interval, id="uav_position_update", args=[])
        self.set_uav_position([0, 0])
        self.gps = GPSBridge(self.tag)

        self.utm_interface = network_sockets.TcpPersistent(self.utm_packet_handler, debug=False, port=55555, interface='')
        self.uas_interface = network_sockets.UdpInterface(self.uas_packet_handler, debug=False, port=44444, interface='')
        self.utm_interface.start()
        self.uas_interface.start()
        self.etcd = etcd3.client()
        self.scheduler.add_job(self.compare_distances, 'interval', seconds=5, id="compare_distances", args=[], max_instances=3)
        self.etcd.add_watch_callback('wt', self.etcd_callback, range_end='wt999')

    def calculate_distance(self, x1, y1, x2, y2):
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

    def compare_distances(self):
        inspector = self.tag
        inspector_position = self.get_uav_position()
        x2, y2, _ = inspector_position

        to_write = []

        for aircraft_id, (x1, y1) in self.wt_coordinates.items():
            distance = self.calculate_distance(x1, y1, x2, y2)
            if distance < 65:
                data = json.dumps({
                    "inspected_WT": aircraft_id,
                    "inspected_WT_position": (x1, y1),
                    "inspector_UAV": inspector,
                    "inspector_UAV_position": inspector_position,
                    "distance": distance,
                })
                to_write.append((str(aircraft_id), data))

        for aircraft_id, data in to_write:
            self.write_to_etcd(aircraft_id, data)

    def write_to_etcd(self, aircraft_id, data):
        self.visited_wt += 1
        try:
            status = self.etcd.status()
            if status.leader is not None:
                try:
                    if self.etcd.get(str(aircraft_id)) == (None, None):
                        try:
                            self.etcd.put(aircraft_id, data)
                            print(self.tag, "ETCD SAVED FOR", aircraft_id, ":", data)
                        except Exception as e:
                            print(self.tag, "Error while adding data to ETCD:", str(e))
                except Exception as e:
                    print(self.tag, "Error while searching for key in the ETCD:", str(e))
        except Exception as e:
            print(self.tag, "UTMServer>write_to_etcd>Error while checking ETCD status:", str(e))

    def save_historic_local(self, aircraft_id, data):
        if aircraft_id not in self.data_bank_local:
            self.data_bank_local[aircraft_id] = data
            data_dict = json.loads(data)
            inspected_WT_position = data_dict['inspected_WT_position']
            inspector_UAV = data_dict['inspector_UAV']
            inspector_UAV_position = data_dict['inspector_UAV_position']
            inspecting_distance = data_dict['distance']
            data_str = str(int(time.time() * 1000000)) + ";" + str(aircraft_id) + ";" + str(inspected_WT_position) + ";" + str(inspector_UAV) + ";" + str(inspector_UAV_position) + ";" + str(inspecting_distance) + ";" + "local"
            print(f"{self.tag} LOCAL SAVED FOR {aircraft_id}:", data_str)
            self.check_data_bank_completion()

    def is_data_already_saved(self, aircraft_id):
        return aircraft_id in self.data_bank_etcd

    def save_historic_etcd(self, aircraft_id, data):
        self.data_bank_etcd[aircraft_id] = data

    def check_data_bank_completion(self):
        required_keys = {f"wt{i}" for i in range(1, 10)}
        current_keys = set(self.data_bank_etcd.keys())
        if required_keys <= current_keys:
            print("==========================================================================================")
            print(self.tag, "finished its mission.")
            print("==========================================================================================")

    def etcd_callback(self, _event):
        try:
            for event in _event.events:
                aircraft_data, _ = self.etcd.get(event.key)
                aircraft_data = aircraft_data.decode()
                data_dict = json.loads(aircraft_data)
                aircraft_id = event.key.decode()
                if not self.is_data_already_saved(aircraft_id):
                    inspected_WT_position = data_dict['inspected_WT_position']
                    inspector_UAV = data_dict['inspector_UAV']
                    inspector_UAV_position = data_dict['inspector_UAV_position']
                    inspecting_distance = data_dict['distance']
                    data_str = str(int(time.time() * 1000000)) + ";" + str(aircraft_id) + ";" + str(inspected_WT_position) + ";" + str(inspector_UAV) + ";" + str(inspector_UAV_position) + ";" + str(inspecting_distance) + ";" + "etcd"
                    self.save_historic_etcd(aircraft_id, data_str)
                    print(self.tag, "Data got from etcd is saving: ", data_str)
                    self.check_data_bank_completion()
        except Exception as e:
            print(self.tag, "UTMServer>etcd_callback>Error getting data from ETCD: " + str(e))

    def set_uav_position(self, pos):
        self.surface_position = pos

    def uav_position_update(self):
        self.previous_position = self.get_uav_position()
        position = self.gps.get_position()
        position = pickle.loads(position)
        if position == [-1, -1, -1]:
            self.set_uav_position([100, 100])
        else:
            self.set_uav_position(position)
        created = str(int(time.time() * 1000000))
        identification = self.tag
        position = self.get_uav_position()
        if self.previous_position != [0, 0]:
            last_distance_travelled = math.sqrt((pow((self.previous_position[0] - position[0]), 2)) + (pow((self.previous_position[1] - position[1]), 2)))
            self.flying_distance += last_distance_travelled
            self.save_position(created, identification, position, self.flying_distance)

    def save_position(self, created, identification, current_position, flying_distance):
        try:
            if not self.position_skip:
                pos = str(int(time.time() * 1000000)) + ';' + str(created) + ';' + str(identification) + ';' + str(current_position) + ';' + str(flying_distance) + ';' + str(self.visited_wt)
                self.uav_position_tracker.append(pos)
        except:
            pass

    def get_uav_position(self):
        return self.surface_position

    def save_to_file(self):
        print("=============The final save method is being executed================")
        try:
            for data in self.data_bank_etcd.values():
                self.report_file.write(data + '\n')
        except:
            logging.error("UTMServer>save_to_file>Error saving databank to file")
        self.report_file.flush()
        self.report_file.close()

        try:
            for uav_position in self.uav_position_tracker:
                self.position_file.write(uav_position + '\n')
            self.position_file.flush()
            self.position_file.close()
            self.etcd.close()
        except:
            logging.error("UTMServer>save_to_file>Error saving databank to position file")

    def utm_packet_handler(self, payload, sender_ip, connection):
        pass

    def uas_packet_handler(self, payload, sender_ip, connection):
        pass

def parse_args():
    parser = argparse.ArgumentParser(description='Some arguments are obligatory and must follow the correct order as indicated')
    parser.add_argument("-t", "--tag", help="Tag name", type=str)
    return parser.parse_args()

def set_logging():
    logging.Formatter('%(asctime)s -> [%(levelname)s] %(message)s')
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logging.basicConfig(level='INFO')

if __name__ == '__main__':
    set_logging()
    logging.info("Starting UTM server")
    args = parse_args()
    try:
        UTMServer(args.tag, 18000)
    except KeyboardInterrupt:
        logging.info("Exiting UTM Server")
