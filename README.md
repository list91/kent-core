# Kent Core Sensor Service

Сервис для непрерывного сбора данных с LiDAR датчика VL53L5CX и камеры на Raspberry Pi с последующей раздачей данных по сети.

## Описание

Сервис состоит из двух процессов:

- **Reader Process** - непрерывно считывает данные с датчиков и сохраняет их в общие файлы
- **Listener Process** - принимает сетевые запросы и отдает последние данные с датчиков

### Ключевые особенности

- ✅ **Оптимизированная инициализация**: LiDAR датчик инициализируется один раз при запуске
- ✅ **Непрерывная работа**: Reader работает в бесконечном цикле без остановки
- ✅ **Атомарная запись**: Данные сохраняются атомарно через временные файлы
- ✅ **Синхронизация**: Все данные помечаются одинаковым timestamp
- ✅ **Отказоустойчивость**: Сервис продолжает работу при отказе одного из датчиков
- ✅ **Многопоточность**: Listener поддерживает множественные соединения
- ✅ **Graceful shutdown**: Корректная остановка по сигналам

## Структура проекта

```
kent-core/
├── sensor_service/
│   ├── __init__.py          # Python пакет
│   ├── config.py            # Конфигурация
│   ├── utils.py             # Утилиты
│   ├── reader.py            # Reader процесс
│   └── listener.py          # Listener процесс
├── scripts/
│   ├── install.sh           # Установка
│   ├── start_service.sh     # Запуск сервиса
│   ├── stop_service.sh      # Остановка сервиса
│   └── status.sh            # Статус сервиса
├── tests/
│   ├── test_client.py       # Тестовый клиент
│   ├── test_utils.py        # Unit тесты
│   └── test_integration.py  # Интеграционные тесты
├── logs/                    # Логи (создается автоматически)
└── README.md               # Этот файл
```

## Установка

### Предварительные требования

- Raspberry Pi с подключенными датчиками VL53L5CX и камерой
- Python 3.9+
- Библиотека VL53L5CX для Python
- libcamera-apps для работы с камерой

### Быстрая установка

```bash
cd ~/tools/kent-core
chmod +x scripts/install.sh
./scripts/install.sh
```

Скрипт установки:
- Создаст виртуальное окружение Python
- Установит необходимые зависимости
- Проверит наличие датчиков и библиотек
- Настроит systemd сервис (опционально)

### Ручная установка

```bash
# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install numpy

# Установка VL53L5CX (если есть датчик)
# Следуйте инструкциям для вашей версии библиотеки

# Установка camera tools
sudo apt update
sudo apt install libcamera-apps netcat-openbsd
```

## Использование

### Запуск сервиса

```bash
# Запуск
./scripts/start_service.sh

# Проверка статуса
./scripts/status.sh

# Остановка
./scripts/stop_service.sh
```

### Проверка работы

```bash
# Простая проверка подключения
echo "GET_DATA" | nc localhost 5555

# Подробный тест с сохранением данных
cd tests
python test_client.py --save --output-dir ./received_data

# Непрерывное получение данных
python test_client.py --continuous --interval 2
```

### Просмотр логов

```bash
# Логи Reader процесса
tail -f logs/sensor_reader.log

# Логи Listener процесса
tail -f logs/sensor_listener.log

# Все логи
tail -f logs/*.log
```

## Протокол обмена

### Запрос клиента

```
GET_DATA\n
```

### Ответ сервера

```
TIMESTAMP:<unix_timestamp>\n
IMAGE_SIZE:<bytes>\n
<binary_image_data>
CSV_SIZE:<bytes>\n
<csv_text_data>
END\n
```

### Ошибки

```
ERROR: <error_message>\n
```

Возможные ошибки:
- `ERROR: Invalid command` - неверная команда
- `ERROR: No data available` - данные недоступны
- `ERROR: No fresh data available` - данные устарели (>5 сек)

## Конфигурация

Основные настройки в `sensor_service/config.py`:

```python
# Сеть
LISTENER_PORT = 5555
LISTENER_HOST = "0.0.0.0"

# Тайминги
READING_INTERVAL = 0.5      # Интервал чтения датчиков (сек)
MAX_DATA_AGE = 5.0          # Максимальный возраст данных (сек)

# LiDAR
LIDAR_MIN_DISTANCE = 30     # Минимальная валидная дистанция (мм)
LIDAR_MAX_DISTANCE = 4000   # Максимальная валидная дистанция (мм)

# Камера
CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080
```

## Файлы данных

Сервис сохраняет данные в `/tmp/sensor_data/`:

- `current.jpg` - последнее изображение с камеры
- `current.csv` - последние данные LiDAR в формате CSV
- `timestamp.txt` - временная метка последнего обновления

## Тестирование

### Unit тесты

```bash
cd tests
python test_utils.py
```

### Интеграционные тесты

```bash
cd tests
python test_integration.py
```

### Тестовый клиент

```bash
cd tests

# Одиночный запрос
python test_client.py

# С сохранением данных
python test_client.py --save --output-dir ./received_data

# Непрерывное тестирование
python test_client.py --continuous --interval 1

# Подключение к удаленному серверу
python test_client.py --host 192.168.1.100 --port 5555
```

## Systemd интеграция

Если при установке был выбран systemd сервис:

```bash
# Управление через systemd
sudo systemctl start kent-sensor-service
sudo systemctl stop kent-sensor-service
sudo systemctl status kent-sensor-service
sudo systemctl restart kent-sensor-service

# Автозапуск
sudo systemctl enable kent-sensor-service
sudo systemctl disable kent-sensor-service

# Просмотр логов systemd
journalctl -u kent-sensor-service -f
```

## Мониторинг производительности

### Проверка ресурсов

```bash
# Процессы сервиса
ps aux | grep -E "(sensor_reader|sensor_listener)"

# Использование памяти
pmap $(cat /tmp/kent-sensor-service/sensor_reader.pid)
pmap $(cat /tmp/kent-sensor-service/sensor_listener.pid)

# Использование CPU
top -p $(cat /tmp/kent-sensor-service/sensor_reader.pid),$(cat /tmp/kent-sensor-service/sensor_listener.pid)
```

### Проверка сети

```bash
# Проверка порта
netstat -ln | grep 5555
ss -ln | grep 5555

# Активные соединения
netstat -an | grep 5555
```

## Troubleshooting

### Сервис не запускается

1. Проверьте логи: `tail -f logs/*.log`
2. Проверьте права доступа: `ls -la /tmp/sensor_data`
3. Проверьте виртуальное окружение: `ls -la venv/bin/python3`
4. Проверьте датчики: `python -c "import vl53l5cx; print('VL53L5CX OK')"`

### LiDAR не работает

```bash
# Проверка I2C
sudo i2cdetect -y 1

# Проверка библиотеки
source venv/bin/activate
python -c "from vl53l5cx.vl53l5cx import VL53L5CX; print('VL53L5CX library OK')"
```

### Камера не работает

```bash
# Проверка камеры
libcamera-still --list-cameras

# Тест захвата
libcamera-still -t 1000 -o test.jpg
```

### Сетевые проблемы

```bash
# Проверка порта
nc -z localhost 5555 && echo "Port 5555 is open" || echo "Port 5555 is closed"

# Проверка файервола
sudo ufw status
sudo iptables -L | grep 5555
```

### Устаревшие данные

```bash
# Проверка timestamp
stat /tmp/sensor_data/timestamp.txt
cat /tmp/sensor_data/timestamp.txt

# Сравнение с текущим временем
echo "Current: $(date +%s)"
echo "Data: $(cat /tmp/sensor_data/timestamp.txt)"
```

## Производительность

### Ожидаемые метрики

- **Задержка чтения**: < 100 мс
- **Время ответа**: < 200 мс
- **Использование RAM**: < 100 MB на процесс
- **Использование CPU**: < 20% в среднем
- **Максимум клиентов**: 10 одновременных

### Оптимизация

1. **Увеличение частоты чтения**: уменьшите `READING_INTERVAL` в config.py
2. **Уменьшение размера изображения**: измените `CAMERA_WIDTH` и `CAMERA_HEIGHT`
3. **Настройка LiDAR**: измените `LIDAR_FREQUENCY` для баланса точности/скорости

## Безопасность

- Сервис привязан к `0.0.0.0` - доступен из сети
- Нет аутентификации - используйте файервол или VPN
- Временные файлы в `/tmp` - очищаются при перезагрузке
- Логи могут содержать отладочную информацию

## Лицензия

Этот проект разработан для внутреннего использования Kent Core.

## Поддержка

При возникновении проблем:

1. Проверьте логи: `./scripts/status.sh`
2. Запустите тесты: `cd tests && python test_client.py`
3. Проверьте документацию выше
4. Создайте issue с подробным описанием проблемы и логами