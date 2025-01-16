import time
from RPLCD.i2c import CharLCD

try:
    lcd = CharLCD('PCF8574', 0x27)  # или 0x3F в зависимости от вашего дисплея
    lcd.cursor_pos = (0, 0)  # Перейдите к первой строке
    lcd.write_string('1'*45)
    time.sleep(5)
    lcd.clear()
except Exception as e:
    print(f"Ошибка: {e}")
