import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# 读取CSV文件并跳过第一行
file_path = '/home/mace/pymace/reports/wind_farm/reports20240429/etcd_nofaults4/Folder_2/uav3position.csv'
#file_path = '/home/mace/pymace/reports/wind_farm/reports20240429/bl1_nofaults_mostcompact_65_newmobility/Folder_10/uav1position.csv'

df = pd.read_csv(file_path, sep=';', skiprows=1, header=None)

# 检查CSV文件的前几行
print("CSV 文件的前几行数据：")
print(df.head())

# 提取第四列数据（索引为3）
data = df.iloc[:, 3]

# 将字符串形式的坐标转换为列表
coordinates = data.apply(eval).tolist()

# 提取x和y数据
x_data = [coord[0] for coord in coordinates]
y_data = [coord[1] for coord in coordinates]

# 检查是否有数据
if len(x_data) == 0 or len(y_data) == 0:
    raise ValueError("No valid data found in the specified column.")

# 创建图表
fig, ax = plt.subplots()
line, = ax.plot([], [], 'r-')

# 设置坐标轴范围
ax.set_xlim(0, 1400)
ax.set_ylim(0, 900)

# 更新函数
def update(frame):
    line.set_data(x_data[:frame], y_data[:frame])
    return line,

# 动画
ani = animation.FuncAnimation(fig, update, frames=len(x_data), interval=1, blit=True, repeat=False)


# 绘制完整轨迹
plt.figure()
plt.plot(x_data, y_data, 'r-')
plt.xlim(0, 1400)
plt.ylim(0, 900)
plt.xlabel('X Coordinate')
plt.ylabel('Y Coordinate')
plt.title('Complete Motion Trajectory')

plt.show()
