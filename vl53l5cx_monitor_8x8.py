#!/usr/bin/env python3
import time
import numpy as np
from vl53l5cx.vl53l5cx import VL53L5CX
import datetime
import signal
import sys

def main():
    print('=== VL53L5CX 8x8 Continuous Monitor ===')
    print('Инициализация датчика...')
    
    sensor = VL53L5CX()
    sensor.init()
    
    # Устанавливаем режим 8x8
    if sensor.get_resolution() != 64:
        print('Переключение в режим 8x8...')
        sensor.set_resolution(64)
        sensor.set_ranging_frequency_hz(15)
    
    print(f'Разрешение: {sensor.get_resolution()} (8x8)')
    print(f'Частота: {sensor.get_ranging_frequency_hz()} Hz')
    print('Нажмите Ctrl+C для остановки\n')
    
    sensor.start_ranging()
    
    measurement = 0
    try:
        while True:
            measurement += 1
            time.sleep(0.3)
            
            # Получаем данные
            data = sensor.get_ranging_data()
            distances = np.array(data.distance_mm).reshape(8, 8)
            
            # Очищаем экран
            print('\033[2J\033[H', end='')
            
            # Заголовок
            timestamp = datetime.datetime.now().strftime('%H:%M:%S')
            print(f'=== VL53L5CX 8x8 | {timestamp} | #{measurement} ===\n')
            
            # Матрица с цветами
            print('     ', end='')
            for col in range(8):
                print(f'{col:>5}', end='')
            print('\n   +' + '-' * 40)
            
            for row in range(8):
                print(f'{row}  | ', end='')
                for col in range(8):
                    d = distances[row, col]
                    if d > 0:
                        if d < 100:
                            print(f'\033[91m{d:4.0f}\033[0m ', end='')  # Красный
                        elif d < 500:
                            print(f'\033[93m{d:4.0f}\033[0m ', end='')  # Желтый
                        elif d < 1000:
                            print(f'\033[92m{d:4.0f}\033[0m ', end='')  # Зеленый
                        else:
                            print(f'\033[94m{d:4.0f}\033[0m ', end='')  # Синий
                    else:
                        print(' --- ', end='')
                print()
            
            # Статистика
            valid = distances[distances > 0]
            if len(valid) > 0:
                print(f'\nМин: {np.min(valid):.0f} мм | Макс: {np.max(valid):.0f} мм | Среднее: {np.mean(valid):.0f} мм')
                print(f'Валидных: {len(valid)}/64 ({len(valid)/64*100:.0f}%)')
                
                close = len(valid[valid < 200])
                if close > 0:
                    print(f'🚨 Близких объектов (<200мм): {close}')
    
    except KeyboardInterrupt:
        print('\n\nОстановка...')
    finally:
        sensor.stop_ranging()
        print('Датчик остановлен')

if __name__ == '__main__':
    main()
