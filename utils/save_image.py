#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import time
import glob
from datetime import datetime

# Константы
OUTPUT_DIR = os.path.expanduser("~/tools/kent-core/metrics_data")
MAX_IMAGES = 5

def capture_image(output_path):
    """Захват изображения с камеры с помощью libcamera-still"""
    try:
        # Создаем директорию, если она не существует
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Запускаем libcamera-still для захвата изображения
        cmd = ["libcamera-still", 
               "-t", "1000",       # время ожидания 1 секунда
               "--width", "1920", 
               "--height", "1080", 
               "-o", output_path]
        
        subprocess.run(cmd, check=True)
        print(f"Изображение сохранено в {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при захвате изображения: {e}")
        return False
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")
        return False

def cleanup_old_images(directory, max_files=MAX_IMAGES):
    """Удаление старых изображений, если их количество превышает max_files"""
    try:
        # Получаем список всех jpg файлов в директории
        jpg_files = glob.glob(os.path.join(directory, "*.jpg"))
        
        # Если файлов больше чем max_files, удаляем самые старые
        if len(jpg_files) > max_files:
            # Сортируем файлы по времени изменения (от старых к новым)
            jpg_files.sort(key=os.path.getmtime)
            
            # Определяем, сколько файлов нужно удалить
            files_to_delete = len(jpg_files) - max_files
            
            # Удаляем самые старые файлы
            for i in range(files_to_delete):
                os.remove(jpg_files[i])
                print(f"Удален старый файл: {jpg_files[i]}")
                
        return True
    except Exception as e:
        print(f"Ошибка при очистке старых изображений: {e}")
        return False

def main():
    """Основная функция программы"""
    # Создаем имя файла с текущей временной меткой
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"cam_image_{timestamp}.jpg"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    # Захватываем изображение
    capture_success = capture_image(output_path)
    
    # Если изображение успешно захвачено, проверяем необходимость очистки
    if capture_success:
        cleanup_old_images(OUTPUT_DIR)

if __name__ == "__main__":
    main()
