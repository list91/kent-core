import time, numpy as np
from vl53l5cx.vl53l5cx import VL53L5CX

sensor = VL53L5CX()
sensor.init()
sensor.start_ranging()
time.sleep(1)
data = sensor.get_ranging_data()
distances = np.array(data.distance_mm).reshape(8, 8)

print('Матрица расстояний (мм):')
for row in distances:
    print(' '.join(f'{d:4.0f}' if d > 0 else ' ---' for d in row))

valid = distances[distances > 0]
if len(valid) > 0:
    print(f'Мин: {np.min(valid):.0f}, Макс: {np.max(valid):.0f}, Среднее: {np.mean(valid):.0f}')

sensor.stop_ranging()
