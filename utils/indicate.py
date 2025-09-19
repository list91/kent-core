import requests

def get_usd_to_rub_rate():
    try:
        response = requests.get("https://www.cbr-xml-daily.ru/daily_json.js")
        response.raise_for_status()  # Проверка на успешный ответ
        data = response.json()
        usd_rate = data["Valute"]["USD"]["Value"]
        return usd_rate
    except requests.RequestException as e:
        print(f"Ошибка запроса: {e}")
        return None
    except KeyError:
        print("Ошибка при обработке данных.")
        return None

# if __name__ == "__main__":
#     rate = get_usd_to_rub_rate()
#     if rate is not None:
#         print(f"Текущий курс доллара к рублю: {rate} ₽")
#     else:
#         print("Не удалось получить курс.")
import time
from RPLCD.i2c import CharLCD
#
try:
    lcd = CharLCD('PCF8574', 0x27)  # или 0x3F в зависимости от вашего дисплея
    while 1:
        
        lcd.clear()
        lcd.cursor_pos = (0, 0)  # Перейдите к первой строке
        lcd.write_string(f"{get_usd_to_rub_rate()} ₽")
        # lcd.write_string('1'*5)
        time.sleep(5)
        lcd.clear()
except Exception as e:
    print(f"Ошибка: {e}")

