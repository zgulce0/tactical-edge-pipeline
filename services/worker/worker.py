import pika
import json
import time
import os
import psycopg

# RabbitMQ ayarları
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "admin")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "admin123")
QUEUE_NAME = os.getenv("QUEUE_NAME", "sensor_data")

# PostgreSQL ayarları
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "sensordata")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASS = os.getenv("DB_PASS", "admin123")

# Anomali eşiği: bu sıcaklığın üzerini "anomali" say
TEMPERATURE_THRESHOLD = float(os.getenv("TEMPERATURE_THRESHOLD", 40))


def connect_to_db():
    """PostgreSQL'e bağlanmayı dener, bağlanana kadar tekrar dener."""
    while True:
        try:
            conn = psycopg.connect(
                host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
                user=DB_USER, password=DB_PASS,
            )
            print(f"[OK] PostgreSQL'e bağlanıldı: {DB_HOST}:{DB_PORT}")
            return conn
        except psycopg.OperationalError:
            print("[HATA] PostgreSQL'e bağlanılamadı, 3 saniye sonra tekrar denenecek...")
            time.sleep(3)


def create_table_if_not_exists(conn):
    """Tablo yoksa oluşturur."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id SERIAL PRIMARY KEY,
                device_id TEXT NOT NULL,
                reading_time TIMESTAMPTZ NOT NULL,
                temperature_celsius REAL,
                battery_percent REAL,
                signal_strength_dbm REAL,
                latitude REAL,
                longitude REAL,
                is_anomaly BOOLEAN,
                processed_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        conn.commit()
    print("[OK] Tablo hazır: sensor_readings")


def connect_to_rabbitmq():
    """RabbitMQ'ya bağlanmayı dener, bağlantı kesikse tekrar dener."""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials,
                )
            )
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            print(f"[OK] RabbitMQ'ya bağlanıldı: {RABBITMQ_HOST}:{RABBITMQ_PORT}")
            return connection, channel
        except pika.exceptions.ProbableAuthenticationError:
            print("[HATA] Kimlik doğrulama başarısız! Kullanıcı adı/şifre yanlış.")
            time.sleep(3)
        except pika.exceptions.AMQPConnectionError:
            print("[HATA] RabbitMQ'ya bağlanılamadı, 3 saniye sonra tekrar denenecek...")
            time.sleep(3)


def process_message(conn, body):
    """Bir mesajı işler: anomali kontrolü yapar, veritabanına yazar."""
    data = json.loads(body)
    is_anomaly = data["temperature_celsius"] > TEMPERATURE_THRESHOLD

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO sensor_readings
            (device_id, reading_time, temperature_celsius, battery_percent,
             signal_strength_dbm, latitude, longitude, is_anomaly)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data["device_id"], data["timestamp"], data["temperature_celsius"],
            data["battery_percent"], data["signal_strength_dbm"],
            data["latitude"], data["longitude"], is_anomaly,
        ))
        conn.commit()

    tag = "[ANOMALİ!]" if is_anomaly else "[NORMAL]"
    print(f"{tag} {data['device_id']} - {data['temperature_celsius']}°C - kaydedildi")


def main():
    db_conn = connect_to_db()
    create_table_if_not_exists(db_conn)

    while True:
        mq_conn, channel = connect_to_rabbitmq()

        def callback(ch, method, properties, body):
            try:
                process_message(db_conn, body)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                print(f"[HATA] Mesaj işlenemedi: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

        print("[BEKLİYOR] Mesajlar dinleniyor, çıkmak için Ctrl+C...")
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            print("\n[DURDURULDU] Worker kapatılıyor.")
            mq_conn.close()
            db_conn.close()
            break
        except (pika.exceptions.ConnectionClosedByBroker,
                pika.exceptions.StreamLostError,
                pika.exceptions.AMQPConnectionError):
            print("[HATA] RabbitMQ bağlantısı koptu, yeniden bağlanılıyor...")
            continue


if __name__ == "__main__":
    main()