#!/usr/bin/env python3
import time
import numpy as np
from vl53l5cx.vl53l5cx import VL53L5CX
import datetime
import signal
import sys

class VL53L5CXMonitor:
    def __init__(self):
        self.sensor = None
        self.running = True
        
    def signal_handler(self, signum, frame):
        print('\n\n=== Остановка мониторинга ===')
        self.running = False
        if self.sensor:
            try:
                self.sensor.stop_ranging()
                print('Датчик остановлен')
            except:
                pass
        sys.exit(0)
    
    def init_sensor(self):
        print('=== VL53L5CX Continuous Monitor ===')
        print('Инициализация датчика...')
        try:
            self.sensor = VL53L5CX()
            self.sensor.init()
            self.sensor.start_ranging()
            print('Датчик готов к работе!')
            print('Нажмите Ctrl+C для остановки\n')
            return True
        except Exception as e:
            print(f'Ошибка инициализации: {e}')
            return False
    
    def get_distance_matrix(self):
        try:
            data = self.sensor.get_ranging_data()
            distances = np.array(data.distance_mm).reshape(8, 8)
            return distances, data
        except Exception as e:
            print(f'Ошибка получения данных: {e}')
            return None, None
    
    def print_matrix(self, distances, measurement_count):
        # Clear screen (works on most terminals)
        print('\033[2J\033[H', end='')
        
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f'=== VL53L5CX Monitor | {timestamp} | Измерение #{measurement_count} ===\n')
        
        print('Матрица расстояний (мм):')
        print('     ', end='')
        for col in range(8):
            print(f'{col:>5}', end='')
        print('\n   +' + '-' * 40)
        
        for row in range(8):
            print(f'{row}  | ', end='')
            for col in range(8):
                distance = distances[row, col]
                if distance > 0:
                    # Color coding for different ranges
                    if distance < 100:
                        print(f'\033[91m{distance:4.0f}\033[0m ', end='')  # Red for very close
                    elif distance < 500:
                        print(f'\033[93m{distance:4.0f}\033[0m ', end='')  # Yellow for close
                    elif distance < 1000:
                        print(f'\033[92m{distance:4.0f}\033[0m ', end='')  # Green for medium
                    else:
                        print(f'\033[94m{distance:4.0f}\033[0m ', end='')  # Blue for far
                else:
                    print(' --- ', end='')
            print()
        
        # Statistics
        valid_distances = distances[distances > 0]
        if len(valid_distances) > 0:
            print(f'\nСтатистика:')
            print(f'  📏 Минимум: {np.min(valid_distances):.0f} мм')
            print(f'  📏 Максимум: {np.max(valid_distances):.0f} мм') 
            print(f'  📊 Среднее: {np.mean(valid_distances):.0f} мм')
            print(f'  ✅ Валидных точек: {len(valid_distances)}/64 ({len(valid_distances)/64*100:.1f}%)')
            
            # Detect close objects
            close_objects = len(valid_distances[valid_distances < 200])
            if close_objects > 0:
                print(f'  🚨 Близких объектов (<200мм): {close_objects}')
        else:
            print('\n❌ Нет валидных измерений!')
        
        print(f'\n⏱️  Следующее измерение через 1 секунду...')
    
    def run(self):
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        if not self.init_sensor():
            return
        
        measurement_count = 0
        
        try:
            while self.running:
                measurement_count += 1
                
                # Get data from sensor
                distances, raw_data = self.get_distance_matrix()
                
                if distances is not None:
                    self.print_matrix(distances, measurement_count)
                else:
                    print(f'Ошибка получения данных в измерении #{measurement_count}')
                
                # Wait 1 second
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.signal_handler(signal.SIGINT, None)
        except Exception as e:
            print(f'Неожиданная ошибка: {e}')
        finally:
            if self.sensor:
                try:
                    self.sensor.stop_ranging()
                except:
                    pass

if __name__ == '__main__':
    monitor = VL53L5CXMonitor()
    monitor.run()
