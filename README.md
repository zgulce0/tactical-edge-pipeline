# Tactical Edge Data Pipeline

Kesinti toleranslı, container tabanlı saha veri işleme hattı. Sınırlı veya kesintili
ağ bağlantısına sahip ortamlarda (edge computing senaryoları) çalışacak şekilde
tasarlanmış, tamamen self-hosted ve ücretsiz açık kaynak araçlarla kurulmuş bir sistem.

## Mimari

- **sensor-simulator**: sahte sensör verisi üreten servis
- **worker**: mesaj kuyruğundan veri okuyup işleyen servis
- **RabbitMQ/Redis**: servisler arası mesaj kuyruğu
- **PostgreSQL**: işlenmiş verinin depolandığı veritabanı
- **Prometheus + Grafana**: canlı izleme ve metrik toplama
- **k3s**: lokal Kubernetes cluster
- **GitHub Actions**: CI/CD pipeline (build, test, GHCR'a push)

## Durum

Geliştirme aşamasında. Detaylı yol haritası `docs/` klasöründe.

## Klasör yapısı

```
services/       her mikroservisin kodu ve Dockerfile'ı
infra/docker/   docker-compose.yml ve orkestrasyon dosyaları
infra/k8s/      k3s Deployment/Service manifestleri
docs/           notlar, mimari diyagram
```