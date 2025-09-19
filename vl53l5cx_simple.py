#!/usr/bin/env python3
import time
import numpy as np
from vl53l5cx.vl53l5cx import VL53L5CX

def main():
    print('=== VL53L5CX Simple Loop ===')
    
    # Initialize sensor
    sensor = VL53L5CX()
    sensor.init()
    sensor.start_ranging()
    
    try:
        measurement = 0
        while True:
            measurement += 1
            time.sleep(1)  # Wait 1 second
            
            # Get data
            data = sensor.get_ranging_data()
            distances = np.array(data.distance_mm).reshape(8, 8)
            
            # Print matrix
            print(f'\n--- Измерение #{measurement} ---')
            for row in distances:
                print(' '.join(f'{d:4.0f}' if d > 0 else ' ---' for d in row))
            
            # Quick stats
            valid = distances[distances > 0]
            if len(valid) > 0:
                print(f'Мин: {np.min(valid):.0f}мм, Макс: {np.max(valid):.0f}мм, Среднее: {np.mean(valid):.0f}мм')
            
    except KeyboardInterrupt:
        print('\nОстановка...')
    finally:
        sensor.stop_ranging()
        print('Датчик остановлен')

if __name__ == '__main__':
    main()
