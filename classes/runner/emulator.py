""" 
Emulator class
"""
__author__ = "Bruno Chianca Ferreira"
__license__ = "MIT"
__version__ = "0.2"
__maintainer__ = "Bruno Chianca Ferreira"
__email__ = "brunobcf@gmail.com"


import traceback, os, logging, time, subprocess, threading, sys, requests
from classes.runner.runner import Runner

from ..interfaces import iosocket
from ..interfaces import emulation_interface

from core.emulator.coreemu import CoreEmu
from core.emulator.data import IpPrefixes, NodeOptions
from core.emulator.enumerations import NodeTypes, EventTypes
from core.location.mobility import BasicRangeModel
from core import constants
from core.nodes.base import CoreNode
from core.nodes.network import WlanNode

from core.emane.models.ieee80211abg import EmaneIeee80211abgModel
from core.emane.models.rfpipe import EmaneRfPipeModel
from core.emane.models.tdma import EmaneTdmaModel
from core.emane.nodes import EmaneNet

from classes.mobility import mobility

from classes.nodes.fixed_node import FixedNode
from classes.scenario.scenario import Scenario


class Emulator(Runner):
  """_summary_

  Args:
      Runner (_type_): _description_
  """



  def __init__(self, daemon):
    """_summary_

    Args:
        daemon (_type_): _description_
    """
    self.nodes_digest = {}
    self.iosocket_semaphore = False
    self.fixed_nodes = []
    self.mobile_nodes = []
    self.node_options_fixed = []
    self.node_options_mobile = []
    self.core_nodes_fixed = []
    self.core_nodes_mobile = []
    self.daemon_mode = daemon
    self.running = False
    self.try_to_clean()
    self.coreemu = CoreEmu()
    #self.setup(scenario)
    

  def setup(self, scenario_config):
    """_summary_

    Args:
        scenario_config (_type_): _description_
    """
    self.scenario = Scenario(scenario_config)

  def callback(self):
    pass

  def set_daemon_socket(self, socket):
    """_summary_

    Args:
        socket (_type_): _description_
    """
    self.daemon_socket = socket

  def start(self):
    """_summary_
    """
    #pass
    self.running = True
    self.run()

  def try_to_clean(self):
    """_summary_
    """
    os.system("core-cleanup")
    #os.system("sudo ip link delete ctrl0.1")
    #os.system("sudo ip link delete vetha.0.1")
    #os.system("sudo ip link delete vetha.1.1")  

  def setup_core(self):
    """_summary_
    """
    self.session = self.coreemu.create_session()
    # must be in configuration state for nodes to start, when using "node_add" below
    self.session.set_state(EventTypes.CONFIGURATION_STATE)

    #Called mobility by CORE, by it is actually more like the radio model
    self.modelname = BasicRangeModel.name

    #TODO: should only call setup wlans, and scenarion decides between pure core or emane
    self.scenario.setup_nodes(self.session)
    self.scenario.setup_wlans(self.session)
    #self.scenario.setup_wlan_emane(self.session)
    self.scenario.setup_links(self.session)

    self.session.instantiate()
    self.session.write_nodes()

  def configure_batman(self, network_prefix, list_of_nodes):
    """_summary_

    Args:
        network_prefix (_type_): _description_
        list_of_nodes (_type_): _description_
    """
    #Configure Batman only on fixed network
    network_prefix = network_prefix.split("/")[0]
    network_prefix = network_prefix.split(".")
    network_prefix[2] = str(int(network_prefix[2]) + 1)
    network_prefix = '.'.join(network_prefix)
    process = []
    ###TODO Change this to do only on fixed nodes
    for node in list_of_nodes:
      shell = self.session.get_node(node, CoreNode).termcmdstring(sh="/bin/bash")
      #command = "ip link set eth0 address 0A:AA:00:00:00:" + '{:02x}'.format(i+2) +  " && batctl if add eth0 && ip link set up bat0 && ip addr add 10.0.1." +str(i+2) + "/255.255.255.0 broadcast 10.0.1.255 dev bat0"
      command = "modprobe batman-adv && batctl ra BATMAN_IV && batctl if add eth0 && ip link set up bat0 && ip addr add " + network_prefix +str(node) + "/255.255.255.0 broadcast 10.0.1.255 dev bat0"
      shell += " -c '" + command + "'"
      node = subprocess.Popen([
                    "xterm",
                    "-e",
                    shell], stdin=subprocess.PIPE, shell=False)
      process.append(node)

  def server_thread(self):
    """ 
    """
    'Starts a thread with the Socket.io instance that will serve the HMI'
    #mobile_lan = self.scenario.get_wlans()['mobile']
    wlans = self.scenario.get_wlans()
    #print(wlans)
    #sys.exit(1)
    nodes = []
    corenodes = self.scenario.get_mace_nodes()
    for node in corenodes:
      nodes.append(node.corenode)
    self.iosocket = emulation_interface.Socket(nodes, wlans, self.session, self.modelname, self.nodes_digest, self.iosocket_semaphore, self, self.callback, self.scenario.get_networks(), self.scenario.mace_nodes, self.daemon_socket)

  def killsim(self):
    """_summary_
    """

    os.system("sudo killall xterm")
    self.try_to_clean()

    pid = os.popen("ps aux  |grep \"pymace.py\" | grep -v \"grep\" | awk '{print $2}'").readlines()
    for p in pid:
      os.system("sudo kill -s 9 " + str(p))

  def stop(self):
    """_summary_
    """
    print("emulator> #################################################STOP###################################################")
    self.scenario.stop()
    self.running = False

  def run(self):
    """Runs the emulation of a heterogeneous scenario
    """

    ###Ulysses adding
    filename = "/home/mace/pymace/reports/wind_farm/results_temp/uav_communication_overhead_results.txt" 
    
    try:
        #Setup and Start core
        if self.scenario == None:
          logging.error("Load scenario before")
          return
        self.setup_core()
    
    
        ###Ulysses adding
        print("before: the beginning of run")
        initial_results = self.capture_communication_overhead()
        print(initial_results)
    
    
    
        #Setup mobility
        self.scenario.configure_mobility(self.session)
    
        #start dumps
        #if self.scenario.dump:
          #get simdir
        simdir = str(time.localtime().tm_year) + "_" + str(time.localtime().tm_mon) + "_" + str(time.localtime().tm_mday) + "_" + str(time.localtime().tm_hour) + "_" + str(time.localtime().tm_min)
    
        self.scenario.tcpdump(self.session, simdir)
    
        #Start socketio thread
        sthread = threading.Thread(target=self.server_thread, args=())
        sthread.start()
    
        #Start routing and applications
        self.scenario.start_routing(self.session)
        self.scenario.start_applications(self.session)
    
        while self.scenario.running:
          time.sleep(0.1)
    
    ###Ulysses adding

    except KeyboardInterrupt:
        pass
        # Capture communication overhead when the program is interrupted
        #print("Interrupted: capturing current communication overhead before exiting")
        #current_results = self.capture_communication_overhead()
        #print("current_results:",current_results)
        #traffic_difference, totals = self.calculate_traffic_difference(initial_results, current_results)
        #self.save_results_to_file(traffic_difference, totals, filename)

    finally:
    
        print("#################################################STOP###################################################")
                
        print("after: the end of run")
        final_results = self.capture_communication_overhead()
        print("finally_results:", final_results)
        traffic_difference, totals = self.calculate_traffic_difference(initial_results, final_results)
        self.save_results_to_file(traffic_difference, totals, filename)
    
    ###Ulysses adding finished
    
        if not self.daemon_mode: 
          # shutdown session
          logging.info("Simulation finished. Killing all processes")
          requests.get('http://localhost:5000/sim/stop')
    
          sthread.join()
          self.session.shutdown()
    
          try:
              self.killsim()
              os.system("sudo killall xterm")
              os.system("chown -R " + self.scenario.username + ":" + self.scenario.username + " ./reports")
          except:
              pass
        else:
          self.running = False
          sthread.join()
          self.coreemu.shutdown()
          self.scenario = None
          #self.try_to_clean()


  #Ulysses adding for checking the communication overhead
  def capture_communication_overhead(self):
    
    commands = [
        "cat /sys/class/net/veth1.0.1/statistics/rx_packets",
        "cat /sys/class/net/veth1.0.1/statistics/tx_packets",
        "cat /sys/class/net/veth2.0.1/statistics/rx_packets",
        "cat /sys/class/net/veth2.0.1/statistics/tx_packets",
        "cat /sys/class/net/veth3.0.1/statistics/rx_packets",
        "cat /sys/class/net/veth3.0.1/statistics/tx_packets",
        #"cat /sys/class/net/lo/statistics/rx_packets "
  
    ]
    
    results = {}
    for command in commands:
        # 生成键值，如veth1.0.1_rx_packets
        key = command.split("/")[-3] + "_" + command.split("/")[-1]
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            # 解析命令以用作字典键
            #key = command.split("/")[5] + "_" + command.split("/")[-1]
            # 将成功执行的命令输出（转换为整数）添加到结果字典
            results[key] = int(result.stdout.strip())
        except subprocess.CalledProcessError as e:
            # 如果命令执行失败，添加错误信息
            results[key] = f"Error executing {command}: {e.stderr.strip()}"
    # 返回所有命令的执行结果
    return results
  
  
  def calculate_traffic_difference(self, initial_results, final_results):
    # 计算两个结果集之间的差异
    difference_results = {}
    rx_sum = 0
    tx_sum = 0

    for key in initial_results:
        if key in final_results:
            try:
                difference = final_results[key] - initial_results[key]
                difference_results[key] = difference

                # 根据键的类型累加值
                if "rx_packets" in key:
                    rx_sum += difference
                elif "tx_packets" in key:
                    tx_sum += difference

            except TypeError:
                # 如果结果集中包含错误信息，标记该键的计算为错误
                difference_results[key] = "Error in calculation"
        else:
            difference_results[key] = "Key not found in final results"

    # 把rx_packets和tx_packets的总和也存起来
    totals = {
        "total_rx_packets": rx_sum,
        "total_tx_packets": tx_sum
    }   
    
    return difference_results, totals
  
  
  def save_results_to_file(self, difference_results, totals, filename):
    # 将结果保存到文件
    with open(filename, "w") as file:
        # 先写入difference_results的内容
        for key, value in difference_results.items():
            file.write(f"{key} traffic change: {value}\n")
        
        # 添加一个分隔行以清晰区分两部分内容
        file.write("\n--- Totals ---\n")
        
        # 接着写入totals的内容
        for key, value in totals.items():
            file.write(f"{key}: {value}\n")
    
    print(f"Results and totals saved to {filename}")

