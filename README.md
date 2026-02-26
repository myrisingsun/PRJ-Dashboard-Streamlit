# AFI Project Portfolio Dashboard

Многостраничный дашборд управления проектным портфелем на базе **Streamlit**, подключённый к **Google Sheets** как единому источнику данных.

## Стек технологий

| Компонент | Версия |
|---|---|
| Python | 3.11 |
| Streamlit | ≥ 1.35 |
| streamlit-authenticator | ≥ 0.3.2 |
| gspread | 6.x |
| pandas | ≥ 2.0 |
| plotly | ≥ 5.18 |
| Docker + docker-compose | — |

## Структура проекта

```
PRJ-Dashboard-Streamlit/
├── app.py                   # Главная страница (навигация + приветствие)
├── auth.py                  # Аутентификация (streamlit-authenticator)
├── config.yaml              # Учётные данные пользователей (bcrypt) ← НЕ в git
├── config.yaml.example      # Шаблон config.yaml
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env                     # Секреты для Docker ← НЕ в git
├── .env.example             # Шаблон .env
├── .streamlit/
│   └── secrets.toml         # Google Sheet ID + Service Account ← НЕ в git
├── data/
│   └── loader.py            # Загрузка и парсинг данных из Google Sheets
├── components/
│   ├── finance_table.py
│   ├── gantt_chart.py
│   └── status_badge.py
└── pages/
    ├── 1_Index.py           # Портфель проектов
    ├── 2_Gantt.py           # Диаграмма Ганта
    ├── 3_Finance.py         # Финансы 2026
    ├── 4_Team.py            # Команды + калькулятор премий
    ├── 5_Operations.py      # Операционная деятельность
    └── 9_Debug.py           # Диагностика сырых данных
```

## Источники данных (Google Sheets)

| Лист | Назначение |
|---|---|
| `01.PRJ_LIST` | Реестр проектов (мастер) |
| `02.OPER_LIST` | Операционные задачи |
| `03.PRJ_STATUS` | Ключевые точки план/факт |
| `04.PRJ_TEAM` | Матрица участия команды |
| `05.PRJ_MONEY_2026` | Финансы: бюджет, план, факт оплат |

## Локальный запуск

### 1. Зависимости

```bash
pip install -r requirements.txt
```

### 2. Настройка учётных данных Google

Создайте файл `.streamlit/secrets.toml` по образцу:

```toml
GOOGLE_SHEET_ID = "ВАШ_ID_ТАБЛИЦЫ"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "...@....iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
universe_domain = "googleapis.com"
```

### 3. Настройка пользователей

Скопируйте шаблон и заполните:

```bash
cp config.yaml.example config.yaml
```

Сгенерируйте bcrypt-хеш пароля:

```bash
python -c "import bcrypt; print(bcrypt.hashpw('ВАШ_ПАРОЛЬ'.encode(), bcrypt.gensalt(12)).decode())"
```

### 4. Запуск

```bash
streamlit run app.py --server.port 8501
```

Откройте [http://localhost:8501](http://localhost:8501).

## Деплой на VPS (Docker)

### 1. Подготовьте `.env`

```bash
cp .env.example .env
# Заполните GOOGLE_SHEET_ID и GCP_SERVICE_ACCOUNT_JSON
```

### 2. Подготовьте `config.yaml`

```bash
cp config.yaml.example config.yaml
# Заполните пользователей и cookie key
```

### 3. Запустите контейнер

```bash
docker-compose up -d --build
```

## Обновление данных

- **Автоматически** — каждые 5 минут (TTL кэша `@st.cache_data`)
- **Вручную** — кнопка **🔄 Обновить данные** в боковом меню (сбрасывает весь кэш)

## Конфигурационные файлы — что куда

| Файл | В git | Назначение |
|---|---|---|
| `config.yaml` | ❌ | Пользователи + cookie key |
| `config.yaml.example` | ✅ | Шаблон для новых установок |
| `.env` | ❌ | Секреты для Docker (Sheet ID + SA JSON) |
| `.env.example` | ✅ | Шаблон .env |
| `.streamlit/secrets.toml` | ❌ | Секреты для локального запуска |

## Безопасность

- Пароли хранятся только в виде bcrypt-хешей (12 раундов соли)
- Приватный ключ Google Service Account — только в `.env` и `secrets.toml`, оба файла в `.gitignore`
- Cookie-сессии подписаны секретным ключом из `config.yaml`

## Лицензия

Внутренний проект AFI. Распространение запрещено.
