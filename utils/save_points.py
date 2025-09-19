#!/usr/bin/env python3
import time
import numpy as np
from vl53l5cx.vl53l5cx import VL53L5CX
import datetime
import os
import glob
import csv

def manage_csv_files(directory, max_files=5):
    """Управление количеством CSV файлов в директории"""
    # Получаем список всех CSV файлов
    csv_files = glob.glob(os.path.join(directory, "distance_points_*.csv"))
    
    # Если файлов больше max_files, удаляем старые
    if len(csv_files) >= max_files:
        # Сортируем по времени модификации
        csv_files.sort(key=lambda x: os.path.getmtime(x))
        # Удаляем старые файлы
        files_to_delete = len(csv_files) - max_files + 1  # +1 чтобы освободить место для нового
        for i in range(files_to_delete):
            os.remove(csv_files[i])
            print(f"Удален старый файл: {os.path.basename(csv_files[i])}")

def main():
    print('=== VL53L5CX 8x8 Single Measurement ===')
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
    
    # Пороги для определения "хороших" измерений
    MIN_VALID_DISTANCE = 30    # мм
    MAX_VALID_DISTANCE = 4000   # мм
    
    # Создаем директорию если не существует
    data_dir = os.path.expanduser("~/tools/kent-core/metrics_data")
    os.makedirs(data_dir, exist_ok=True)
    
    # Управляем количеством файлов
    manage_csv_files(data_dir, max_files=5)
    
    print('\nВыполнение измерения...')
    sensor.start_ranging()
    
    # Ждем стабилизации датчика
    time.sleep(0.5)
    
    # Получаем данные
    data = sensor.get_ranging_data()
    distances = np.array(data.distance_mm).reshape(8, 8)
    
    # Обрабатываем данные: невалидные точки помечаем как -1
    processed_distances = np.copy(distances)
    for row in range(8):
        for col in range(8):
            d = distances[row, col]
            # Помечаем невалидные измерения как -1
            if d <= MIN_VALID_DISTANCE or d >= MAX_VALID_DISTANCE or d == 0:
                processed_distances[row, col] = -1
    
    # Останавливаем датчик
    sensor.stop_ranging()
    
    # Формируем имя файла с текущей временной меткой
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = os.path.join(data_dir, f"distance_points_{timestamp}.csv")
    
    # Сохраняем в CSV
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Заголовок с метаданными
        writer.writerow(['# VL53L5CX 8x8 Distance Measurement'])
        writer.writerow([f'# Timestamp: {datetime.datetime.now().isoformat()}'])
        writer.writerow([f'# Min valid distance: {MIN_VALID_DISTANCE} mm'])
        writer.writerow([f'# Max valid distance: {MAX_VALID_DISTANCE} mm'])
        writer.writerow(['# Invalid points marked as: -1'])
        writer.writerow([])
        
        # Заголовок колонок
        header = ['Row\\Col'] + [f'Col_{i}' for i in range(8)]
        writer.writerow(header)
        
        # Данные
        for row in range(8):
            row_data = [f'Row_{row}'] + [f'{processed_distances[row, col]:.0f}' for col in range(8)]
            writer.writerow(row_data)
    
    print(f'\nДанные сохранены в: {filename}')
    
    # Выводим результат на экран
    print('\nМАТРИЦА РАССТОЯНИЙ (мм):')
    print('     ', end='')
    for col in range(8):
        print(f'{col:>6}', end='')
    print('\n   +' + '-' * 48)
    
    valid_count = 0
    invalid_count = 0
    
    for row in range(8):
        print(f'{row}  | ', end='')
        for col in range(8):
            d = processed_distances[row, col]
            if d == -1:
                print('\033[91m    -1\033[0m', end='')  # Красный для невалидных
                invalid_count += 1
            else:
                print(f'{d:6.0f}', end='')
                valid_count += 1
        print()
    
    # Статистика
    print(f'\nСтатистика:')
    print(f'Валидных точек: {valid_count}/64 ({valid_count/64*100:.0f}%)')
    print(f'Невалидных точек: {invalid_count}/64 ({invalid_count/64*100:.0f}%)')
    
    # Статистика по валидным точкам
    valid_points = processed_distances[processed_distances != -1]
    if len(valid_points) > 0:
        print(f'\nДля валидных точек:')
        print(f'Мин: {np.min(valid_points):.0f} мм')
        print(f'Макс: {np.max(valid_points):.0f} мм')
        print(f'Среднее: {np.mean(valid_points):.0f} мм')
    
    print('\nИзмерение завершено.')

if __name__ == '__main__':
    main()

