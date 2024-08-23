import os
import time
import shutil
import re  # 导入正则表达式库，用于从命令中提取文件名中的数字


# 命令列表
commands = [
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_etcd_1.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_etcd_2.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_etcd_3.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_etcd_4.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_etcd_5.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_etcd_6.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_etcd_7.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_etcd_8.json",
    "sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_etcd_9.json",
    "sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_etcd_10.json",
    
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_baseline1_2.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_baseline1_3.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_baseline1_4.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_baseline1_5.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_baseline1_6.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_baseline1_7.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_baseline1_8.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_baseline1_9.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_baseline1_10.json",

    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_baseline2_1.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_baseline2_2.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_baseline2_3.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_baseline2_4.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_baseline2_5.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_baseline2_6.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_baseline2_7.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_baseline2_8.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_baseline2_9.json",
    #"sudo ./pymace.py -s ./Ulysses/scenarios/wt_9_3_batteryfail_mostcompact_baseline2_10.json",
]

# 源文件夹
source_dir = '/home/mace/pymace/reports/wind_farm/results_temp/'

# 目标主文件夹
base_target_dir = '/home/mace/pymace/reports/wind_farm/results/'


for command in commands:
    # 使用正则表达式提取.json文件名中的最后一个数字
    
    match = re.search(r'etcd_(\d+)\.json', command)
    #match = re.search(r'etcd_(\d+)\.json', command)
    if match:
        folder_index = match.group(1)  # 获取匹配到的数字，即文件名中的编号
        current_target_dir = os.path.join(base_target_dir, f"Folder_{folder_index}")

        # 检查文件夹是否已存在
        if not os.path.exists(current_target_dir):
            os.makedirs(current_target_dir)  # 创建文件夹
            os.chmod(current_target_dir, 0o777)  # 设置文件夹权限为777，允许所有用户读写执行
        else:
            print(f"Folder '{current_target_dir}' already exists, skipping creation.")
    
        # 运行命令
        os.system(command)
    
        # 等待3小时
        #print("before sleep", time.time())
        #time.sleep(120)  # 3小时
        #time.sleep(3 * 60 * 60 + 100)  # 3小时
        #print("after sleep", time.time())
    
        # 获取生成的文件列表
        generated_files = os.listdir(source_dir)
    
        # 将文件移动到对应的文件夹
        for filename in generated_files:
            source_path = os.path.join(source_dir, filename)
            target_path = os.path.join(current_target_dir, filename)
    
            # 仅当文件存在时才移动
            if os.path.isfile(source_path):
                shutil.move(source_path, target_path)
                
        print("The moving time is", time.localtime())
    else:
        print(f"Failed to extract folder index from command: {command}")