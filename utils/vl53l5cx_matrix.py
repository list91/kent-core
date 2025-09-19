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
    # Массив для хранения времени последнего валидного измерения
    last_valid_time = np.zeros((8, 8))
    # Массив для хранения последних валидных расстояний
    last_valid_distances = np.zeros((8, 8))
    
    # Пороги для определения "хороших" измерений
    MIN_VALID_DISTANCE = 30    # мм
    MAX_VALID_DISTANCE = 4000   # мм
    
    try:
        while True:
            measurement += 1
            current_time = time.time()
            time.sleep(0.3)

            # Получаем данные
            data = sensor.get_ranging_data()
            distances = np.array(data.distance_mm).reshape(8, 8)
            
            # Обновляем время только для "хороших" измерений
            for row in range(8):
                for col in range(8):
                    d = distances[row, col]
                    # Считаем измерение валидным если:
                    # 1. Расстояние в разумных пределах
                    # 2. Это не 0 (отсутствие данных)
                    if d > MIN_VALID_DISTANCE and d < MAX_VALID_DISTANCE:
                        last_valid_time[row, col] = current_time
                        last_valid_distances[row, col] = d

            # Очищаем экран
            print('\033[2J\033[H', end='')

            # Заголовок
            timestamp = datetime.datetime.now().strftime('%H:%M:%S')
            print(f'=== VL53L5CX 8x8 | {timestamp} | #{measurement} ===\n')

            # Матрица текущих расстояний
            print('ТЕКУЩИЕ РАССТОЯНИЯ (мм):')
            print('     ', end='')
            for col in range(8):
                print(f'{col:>5}', end='')
            print('\n   +' + '-' * 40)

            for row in range(8):
                print(f'{row}  | ', end='')
                for col in range(8):
                    d = distances[row, col]
                    if d > 0:
                        if d < MIN_VALID_DISTANCE or d > MAX_VALID_DISTANCE:
                            # Невалидные значения - серым
                            print(f'\033[90m{d:4.0f}\033[0m ', end='')
                        elif d < 100:
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
            
            # Матрица последних валидных расстояний
            print('\n\nПОСЛЕДНИЕ ВАЛИДНЫЕ РАССТОЯНИЯ (мм):')
            print('     ', end='')
            for col in range(8):
                print(f'{col:>5}', end='')
            print('\n   +' + '-' * 40)
            
            for row in range(8):
                print(f'{row}  | ', end='')
                for col in range(8):
                    d = last_valid_distances[row, col]
                    if d > 0:
                        age = current_time - last_valid_time[row, col]
                        # Цветовая индикация по давности
                        if age < 1:
                            print(f'\033[92m{d:4.0f}\033[0m ', end='')  # Зеленый - свежие
                        elif age < 5:
                            print(f'\033[93m{d:4.0f}\033[0m ', end='')  # Желтый - недавние
                        elif age < 10:
                            print(f'\033[91m{d:4.0f}\033[0m ', end='')  # Красный - старые
                        else:
                            print(f'\033[95m{d:4.0f}\033[0m ', end='')  # Пурпурный - очень старые
                    else:
                        print(' N/A ', end='')
                print()

            # Давность обновления
            print('\n\nДАВНОСТЬ ПОСЛЕДНЕГО ВАЛИДНОГО ИЗМЕРЕНИЯ (секунд):')
            print('     ', end='')
            for col in range(8):
                print(f'{col:>5}', end='')
            print('\n   +' + '-' * 40)
            
            for row in range(8):
                print(f'{row}  | ', end='')
                for col in range(8):
                    if last_valid_time[row, col] > 0:
                        age = current_time - last_valid_time[row, col]
                        
                        # Цветовая индикация
                        if age < 1:
                            print(f'\033[92m{age:4.1f}\033[0m ', end='')  # Зеленый
                        elif age < 5:
                            print(f'\033[93m{age:4.1f}\033[0m ', end='')  # Желтый
                        elif age < 10:
                            print(f'\033[91m{age:4.1f}\033[0m ', end='')  # Красный
                        else:
                            print(f'\033[95m{age:4.0f}\033[0m ', end='')  # Пурпурный
                    else:
                        print(' N/A ', end='')
                print()

            # Статистика
            # Для текущих измерений считаем только валидные
            valid_mask = (distances > MIN_VALID_DISTANCE) & (distances < MAX_VALID_DISTANCE)
            valid = distances[valid_mask]
            
            if len(valid) > 0:
                print(f'\nТекущие валидные ({MIN_VALID_DISTANCE}-{MAX_VALID_DISTANCE}мм):')
                print(f'Мин: {np.min(valid):.0f} мм | Макс: {np.max(valid):.0f} мм | Среднее: {np.mean(valid):.0f} мм')
                print(f'Валидных: {len(valid)}/64 ({len(valid)/64*100:.0f}%)')
                
                # Анализ "мертвых" зон
                never_valid = np.sum(last_valid_time == 0)
                stale_5s = np.sum((current_time - last_valid_time) > 5) - never_valid
                stale_10s = np.sum((current_time - last_valid_time) > 10) - never_valid
                
                if never_valid > 0:
                    print(f'\n⚠️  Никогда не было валидных: {never_valid} точек')
                if stale_5s > 0:
                    print(f'⏰ Не обновлялись >5 сек: {stale_5s} точек')
                if stale_10s > 0:
                    print(f'💀 Не обновлялись >10 сек: {stale_10s} точек')

                close = len(valid[valid < 200])
                if close > 0:
                    print(f'\n🚨 Близких объектов (<200мм): {close}')

    except KeyboardInterrupt:
        print('\n\nОстановка...')
    finally:
        sensor.stop_ranging()
        print('Датчик остановлен')

if __name__ == '__main__':
    main()

