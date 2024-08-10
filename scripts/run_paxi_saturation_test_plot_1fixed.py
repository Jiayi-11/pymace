#!/usr/bin/env python3
""" 
Report scripts is part of a thesis work about distributed systems 
"""
__author__ = "Bruno Chianca Ferreira"
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Bruno Chianca Ferreira"
__email__ = "brunobcf@gmail.com"

# TODO #
# Remove / from the end of indir

libnames = ['pandas']
import sys
for libname in libnames:
    try:
        lib = __import__(libname)
    except:
        print (sys.exc_info())
    else:
        globals()[libname] = lib

import os, shutil, sys, traceback, time, argparse, statistics, subprocess
from matplotlib import markers, pyplot as plt
from matplotlib import ticker as ticker
import numpy as np
import pandas
pd = pandas
pd.__version__
#from scipy.optimize import curve_fit


class Saturation():
    def __init__(self, args) -> None:
        self.report_folder = '/home/mace/pymace/reports/wind_farm/'
        self.destination = '/home/mace/pymace/reports/wind_farm/reports20240311/bl2_nofaults/'
        #self.destination = args.outdir
        #self.original_destination = args.outdir
        #self.clients = [10,20,30,40,60,80,100,200,300,500,1000]

        #if self.destination[-1:] != "/":
        #    self.destination += "/"
        
        #self.scenario_file = 'swarm-paxi-' + args.type + '_'
        #self.destination += args.type + '/'
              
        self.run(args.repeat)  #run the test 
        #self.start_plot("Throughput (req/s)", "Latency (ms)", "Latency (ms)")
        #data = self.report()
        #print(data['150']['0'][10]['throughput'])
        #sys.exit(1)
        #self.plot_composed(data)

    def report(self):
        """_summary_
        """
        experiment_types = []
        experiments = {}
        experiments_data = {}

        #get all experiments
        for (dirpath, dirnames, filenames) in os.walk(self.original_destination):
            experiment_types.extend(dirnames)
            break

        #get all repetitions per experiment
        for exp in experiment_types:
            repetitions = []
            for (dirpath, dirnames, filenames) in os.walk(self.original_destination + exp):
                repetitions.extend(dirnames)
                break
            experiments[exp] = repetitions

        for experiment in experiments.keys():
            experiments_data[experiment] = {}
            for rep in experiments[experiment]:
                #experiments_data[experiment][rep] = []
                try:
                    data = self.get_data(experiment,rep)
                    experiments_data[experiment][rep] = (data)
                except:
                    print("Error getting data, maybe this report file is malformed: " + experiment + ", " + str(rep))

        #print(experiments_data['fixed']['2'])
        return(experiments_data)

    def get_data(self, experiment, rep):
        """_summary_

        Args:
            experiment (_type_): _description_
            rep (_type_): _description_
        """
        files = []
        data = {}
        for (dirpath, dirnames, filenames) in os.walk(self.original_destination + experiment + "/" + rep):
            files.extend(filenames)
            break
        #print(files)
        for file in files:
            number_clients = int(file.split("_")[-1:][0])
            if number_clients in self.clients:
                _data_file = open(self.original_destination + experiment + "/" + rep + "/" + file, "r").readlines()
                if (len(_data_file) > 0 ):
                    #process
                    data[number_clients] = {}
                    data[number_clients]["concurrency"] = 0
                    data[number_clients]["throughput"] = 0
                    data[number_clients]["mean_latency"] = 0
                    data[number_clients]["median_latency"] = 0
                    data[number_clients]["p99_latency"] = 0
                    data[number_clients]["p95_latency"] = 0
                    for line in _data_file:
                        dataline = line.split("=")
                        #print(dataline)
                        if "Concurrency" in dataline[0]:
                            data[number_clients]["concurrency"] = int(dataline[1])
                        if "Throughput" in dataline[0]:
                            data[number_clients]["throughput"] = float(dataline[1])
                        if "mean" in dataline[0]:
                            data[number_clients]["mean_latency"] = float(dataline[1])
                        if "median" in dataline[0]:
                            data[number_clients]["median_latency"] = float(dataline[1])
                        if "p99" in dataline[0]:
                            data[number_clients]["p99_latency"] = float(dataline[1])
                        if "p95" in dataline[0]:
                            data[number_clients]["p95_latency"] = float(dataline[1])    
                else:
                    data[number_clients] = {}
                    data[number_clients]["concurrency"] = 0
                    data[number_clients]["throughput"] = 0
                    data[number_clients]["mean_latency"] = 0
                    data[number_clients]["median_latency"] = 0
                    data[number_clients]["p99_latency"] = 0
                    data[number_clients]["p95_latency"] = 0
        return (data)
    

    def start_plot(self, xlab, ylab, y2lab):
        #config InlineBackend.print_figure_kwargs = {'bbox_inches':None}
        plt.style.use('default')
        #figure(figsize=(6, 6), dpi=150)
        plt.rcParams['text.usetex'] = False
        plt.rcParams['axes.linewidth'] = 0.8
        plt.rcParams['font.size'] = 15
        plt.rcParams['xtick.direction'] = 'in'
        plt.rcParams['ytick.direction'] = 'in'
        plt.rcParams['xtick.major.size'] = 5.0
        plt.rcParams['xtick.minor.size'] = 3.0
        plt.rcParams['ytick.major.size'] = 5.0
        plt.rcParams['ytick.minor.size'] = 3.0
        #plt.ylabel(ylab, fontsize=20)
        #plt.xlabel(xlab, fontsize=20)
        plt.yticks(fontsize=10)
        plt.xticks(fontsize=10)
        #plt.grid(color = '#DDDDDD', linestyle = '--', linewidth = 0.5, which='major', alpha=1)
        self.fig, self.ax1 = plt.subplots(figsize=(7, 6), dpi=150)
        self.ax1.yaxis.set_ticks_position('both')
        self.ax1.xaxis.set_ticks_position('both')
        #self.ax2 = self.ax1.twinx()
        self.ax1.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:.2f}'))
        self.ax1.set_xlabel(xlab, fontsize=17)
        self.ax1.set_ylabel(ylab, fontsize=17)
        #self.ax2.set_ylabel(y2lab, fontsize=21)
        #self.ax1.set_xlim([0, 3000])
        self.ax1.set_ylim([0, 450])
        #plt.subplots_adjust(left=0.3, wspace=0.25, hspace=0.25, bottom=0.13, top=0.91)
        self.ax1.grid(color = '#555555', linestyle = '--', linewidth = 0.4, which='major', alpha=0.8)
        #self.ax2.grid(color = '#555555', linestyle = '--', linewidth = 0.4, which='major', alpha=0.8)
        #ax.xaxis.set_minor_locator(MultipleLocator(5))
        #ax.yaxis.set_minor_locator(MultipleLocator(25))
        self.fig.tight_layout()

    def plot_composed(self, data):
        markers = ["*", "+", "s", "o", "^", "h", "4"]
        current_marker = 0
        color = ["#6495ED", "#ED7D31", "#6495ED", "#ED7D31", "#6495ED", "#ED7D31"] # 自定义颜色列表，每个元素对应一条线的颜色
        current_color = 0
        for exp in sorted(data.keys()):
            print(exp)
            lat = []
            mean = []
            tp = []
            for rep in data[exp].keys():
                print(rep)
                _tp = []
                _lat = []
                _mean = []
                for clients, _data in sorted(data[exp][rep].items()):
                    #print(_data)
                    pass
                    _tp.append(_data['throughput'])
                    _lat.append(_data['median_latency'])
                    #_lat.append(_data['p95_latency'])
                    _mean.append(_data['mean_latency'])
                    

                tp.append(_tp)
                lat.append(_lat)
                mean.append(_mean)
            #averate_tp = statistics.mean(tp)
            #averate_tp = statistics.mean(lat)
            average_tp = list(map(statistics.mean, zip(*tp)))
            print(average_tp)
            average_lat = list(map(statistics.mean, zip(*lat)))
            print(average_lat)
            average_std = list(map(statistics.stdev, zip(*lat)))
            
            
            #self.ax1.plot(average_tp, average_lat, label = 'M='+ str(exp) + ' N=5',linewidth=2.0)
            #self.ax1.scatter(average_tp, average_lat, marker=markers[current_marker], color="black",label = exp)
            self.ax1.errorbar(average_tp, average_lat, yerr=average_std, label = 'N='+ str(exp)+ ' fixed', linewidth=2.0, marker=markers[current_marker])
            #self.ax1.errorbar(average_tp, average_lat, yerr=average_std,label = 'N='+ str(exp)+ ' fixed', linewidth=1.0, marker=markers[current_marker], color="black")
            #self.ax1.errorbar(average_tp, average_lat, yerr=average_std,label = 'M='+ str(exp) + ' N=5', linewidth=1.0, marker=markers[current_marker], color="black")
            # try:
            #     xn = np.linspace(np.min(average_tp),np.max(average_tp),500)
            #     popt, pcov = curve_fit(lambda t, a, b, c: a * np.exp(b * t) + c, average_tp, average_lat, (1, 0.001, 10))
            #     a = popt[0]
            #     b = popt[1]
            #     c = popt[2]

            #     yn = a * np.exp(b * xn) + c
            #     self.ax1.plot(xn, yn,label = exp + "_fit")
            # except:
            #     pass

            #if current_marker < len(markers)-1:
            #    current_marker += 1
            #else:
            #    current_marker = 0

             # 更新 current_marker 和 current_color 变量，使其指向下一个标记符号和颜色
            current_marker = (current_marker + 1) % len(markers)  # 使用取模运算循环使用 markers 列表中的标记符号
            current_color = (current_color + 1) % len(color)  # 使用取模运算循环使用 color 列表中的颜色

            #self.ax1.plot(average_tp, average_mean, label = exp,linewidth=2.0)

        handles, labels = plt.gca().get_legend_handles_labels()
        order = [2,1,0]    

        #plt.legend(loc=5, bbox_to_anchor=(0.4,0.85), fontsize=10)
        plt.legend([handles[idx] for idx in order],[labels[idx] for idx in order],loc=3, bbox_to_anchor=(0.6,0.75), fontsize=14)
        #plt.show()
        self.fig.savefig("test.png")

    
    def run(self, reps):
        try:
            os.mkdir(self.destination)
        except FileExistsError:
            pass
        except:
            print("Error creating report folder. Is it a valid folder?")
        for i in range(0,reps):
            try:
                print("create")
                os.mkdir(self.destination + str(i))
            except FileExistsError:
                pass

                print("before running")
                #report = ''
                #temp = []
                r = self.test()
                print(r)
                if r == 0:
                    # 遍历报告文件夹，寻找文件名前三个字符是'uav'的文件
                    for dirpath, dirnames, filenames in os.walk(self.report_folder):
                        for file in filenames:
                            if file.startswith('uav'):
                                report_path = os.path.join(dirpath, file)
                                destination_path = os.path.join(self.destination + str(i), file)
                                print(f"Copying {file} to: {destination_path}")
                                shutil.copy(report_path, destination_path)
                        break  # 仅查看最顶层的文件夹内容

            
            except:
                print("Error creating report folder. Is it a valid folder?")
            #for _test in self.clients:
            #    report = ''
            #    temp = []
            #    r = self.test(_test)
            #    #print("testing " + str(test) + " ,rep: " + str(i))
            #    if r == 0:
            #        for (dirpath, dirnames, filenames) in os.walk(self.report_folder):
            #            temp.extend(filenames)
            #            break
            #        for file in temp:
            #            if file.split(".")[0] == 'client':
            #                report = file
            #        print("copying to: " + self.destination)
            #        shutil.copy(self.report_folder + report, self.destination + str(i)  + "/client_report_" + str(_test))

    
    def test(self):
        scenario = '/home/mace/pymace/Ulysses/wt_9_3_batteryfail_compact_baseline2.json '
        #scenario += self.scenario_file + str(clients) + ".json"
        try:
            #test_file = open(scenario, "r")
            print("before command")
            proc = subprocess.call(['sudo','/home/mace/pymace/pymace.py', '-s ' + scenario])
        except FileNotFoundError:
            return(-1)
        return(0)

    
    #def test(self, clients):
    #    scenario = 'scenarios/'
    #    scenario += self.scenario_file + str(clients) + ".json"
    #    try:
    #        test_file = open(scenario, "r")
    #        proc = subprocess.call(['sudo','./pymace.py', '-s' + scenario, 'het'])
    #    except FileNotFoundError:
    #        return(-1)
    #    return(0)


if __name__ == '__main__':  #for main run the main function. This is only run when this main python file is called, not when imported as a class
    print("Reporter - Test Paxi on pyMACE and create figure for report")
    print()
    folders = []
    sorted_folders = []
    parser = argparse.ArgumentParser(description='Options as below')
    parser.add_argument('outdir', type=str, help='Input dir where reports are located')
    parser.add_argument('-t','--type', type=str, help='type of teste', default="fixed", choices=['fixed', 'mob'])
    parser.add_argument('-r','--repeat', help='how many times to repeate each test', type=int, default=1)
    arguments = parser.parse_args()

    Saturation(arguments)
    sys.exit()
