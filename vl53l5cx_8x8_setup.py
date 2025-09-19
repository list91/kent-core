#!/usr/bin/env python3
import time
import numpy as np
from vl53l5cx.vl53l5cx import VL53L5CX

def setup_8x8_mode():
    print('=== Настройка VL53L5CX в режим 8x8 ===\n')
    
    # Создаем и инициализируем датчик
    print('Инициализация датчика...')
    sensor = VL53L5CX()
    sensor.init()
    
    # Проверяем текущие настройки
    print('\nТекущие настройки:')
    current_resolution = sensor.get_resolution()
    print(f'  Разрешение: {current_resolution} ({int(np.sqrt(current_resolution))}x{int(np.sqrt(current_resolution))})')
    print(f'  Частота: {sensor.get_ranging_frequency_hz()} Hz')
    print(f'  Режим: {sensor.get_ranging_mode()}')
    
    # Устанавливаем разрешение 8x8 (64 точки)
    print('\nУстановка разрешения 8x8 (64 точки)...')
    sensor.set_resolution(64)  # 8x8 = 64
    
    # Устанавливаем частоту обновления
    print('Установка частоты 15 Hz...')
    sensor.set_ranging_frequency_hz(15)
    
    # Проверяем новые настройки
    print('\nНовые настройки:')
    new_resolution = sensor.get_resolution()
    print(f'  Разрешение: {new_resolution} ({int(np.sqrt(new_resolution))}x{int(np.sqrt(new_resolution))})')
    print(f'  Частота: {sensor.get_ranging_frequency_hz()} Hz')
    print(f'  Режим: {sensor.get_ranging_mode()}')
    
    # Тестируем новый режим
    print('\nТестирование режима 8x8...')
    sensor.start_ranging()
    time.sleep(2)  # Ждем стабилизации
    
    # Получаем данные
    data = sensor.get_ranging_data()
    distances = np.array(data.distance_mm).reshape(8, 8)
    
    print('\nМатрица расстояний 8x8 (мм):')
    print('     ', end='')
    for col in range(8):
        print(f'{col:>5}', end='')
    print('\n   +' + '-' * 40)
    
    for row in range(8):
        print(f'{row}  | ', end='')
        for col in range(8):
            distance = distances[row, col]
            if distance > 0:
                print(f'{distance:4.0f} ', end='')
            else:
                print(' --- ', end='')
        print()
    
    # Статистика
    valid_distances = distances[distances > 0]
    print(f'\nСтатистика:')
    print(f'  Валидных точек: {len(valid_distances)}/64 ({len(valid_distances)/64*100:.1f}%)')
    if len(valid_distances) > 0:
        print(f'  Минимум: {np.min(valid_distances):.0f} мм')
        print(f'  Максимум: {np.max(valid_distances):.0f} мм')
        print(f'  Среднее: {np.mean(valid_distances):.0f} мм')
    
    sensor.stop_ranging()
    print('\n✅ Датчик успешно настроен на режим 8x8!')
    return sensor

if __name__ == '__main__':
    try:
        setup_8x8_mode()
    except Exception as e:
        print(f'\n❌ Ошибка: {e}')
        print('Проверьте подключение датчика и права доступа')
