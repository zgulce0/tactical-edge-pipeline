import pika
import json
import time
import random
import os
from datetime import datetime, timezone

# Ayarları environment variable'dan oku, yoksa varsayılan değer kullan
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "admin")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "admin123")
QUEUE_NAME = os.getenv("QUEUE_NAME", "sensor_data")
SEND_INTERVAL = float(os.getenv("SEND_INTERVAL", 2))  # saniye
DEVICE_ID = os.getenv("DEVICE_ID", "sensor-001")


def connect_to_rabbitmq():
    """RabbitMQ'ya bağlanmayı dener, bağlantı kesikse tekrar dener."""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    port=RABBITMQ_PORT,
                    credentials=credentials,
                )
            )
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            print(f"[OK] RabbitMQ'ya bağlanıldı: {RABBITMQ_HOST}:{RABBITMQ_PORT}")
            return connection, channel
        except pika.exceptions.ProbableAuthenticationError:
            print("[HATA] Kimlik doğrulama başarısız! Kullanıcı adı/şifre yanlış. Environment değişkenlerini kontrol edin.")
            time.sleep(3)
        except (pika.exceptions.AMQPConnectionError, OSError):
            print("[HATA] RabbitMQ'ya bağlanılamadı, 3 saniye sonra tekrar denenecek...")
            time.sleep(3)


def generate_sensor_reading():
    """Sahte bir sensör okuması üretir."""
    return {
        "device_id": DEVICE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_celsius": round(random.uniform(15, 45), 2),
        "battery_percent": round(random.uniform(20, 100), 2),
        "signal_strength_dbm": round(random.uniform(-100, -50), 2),
        "latitude": round(random.uniform(38.0, 40.0), 6),
        "longitude": round(random.uniform(28.0, 32.0), 6),
    }


def main():
    connection, channel = connect_to_rabbitmq()

    try:
        while True:
            reading = generate_sensor_reading()
            message = json.dumps(reading)

            try:
                channel.basic_publish(
                    exchange="",
                    routing_key=QUEUE_NAME,
                    body=message,
                    properties=pika.BasicProperties(delivery_mode=2),  # mesajı kalıcı yap
                )
                print(f"[GÖNDERİLDİ] {message}")
            except (pika.exceptions.ConnectionClosed, pika.exceptions.StreamLostError):
                print("[HATA] Bağlantı koptu, yeniden bağlanılıyor...")
                connection, channel = connect_to_rabbitmq()

            time.sleep(SEND_INTERVAL)

    except KeyboardInterrupt:
        print("\n[DURDURULDU] Simülatör kapatılıyor.")
        connection.close()


if __name__ == "__main__":
    main()