# Project Portfolio Dashboard

Многостраничный дашборд управления проектным портфелем на базе **Streamlit**, подключённый к **Google Sheets** как единому источнику данных.

> [English version below](#english)

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

[MIT](LICENSE)

---

<a name="english"></a>

# Project Portfolio Dashboard

A multi-page project portfolio management dashboard built with **Streamlit**, connected to **Google Sheets** as a single source of truth.

## Tech Stack

| Component | Version |
|---|---|
| Python | 3.11 |
| Streamlit | ≥ 1.35 |
| streamlit-authenticator | ≥ 0.3.2 |
| gspread | 6.x |
| pandas | ≥ 2.0 |
| plotly | ≥ 5.18 |
| Docker + docker-compose | — |

## Project Structure

```
PRJ-Dashboard-Streamlit/
├── app.py                   # Main page (navigation + welcome)
├── auth.py                  # Authentication (streamlit-authenticator)
├── config.yaml              # User credentials (bcrypt) ← NOT in git
├── config.yaml.example      # config.yaml template
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env                     # Docker secrets ← NOT in git
├── .env.example             # .env template
├── .streamlit/
│   └── secrets.toml         # Google Sheet ID + Service Account ← NOT in git
├── data/
│   └── loader.py            # Data loading and parsing from Google Sheets
├── components/
│   ├── finance_table.py
│   ├── gantt_chart.py
│   └── status_badge.py
└── pages/
    ├── 1_Index.py           # Project portfolio (cards + KPIs)
    ├── 2_Gantt.py           # Gantt chart
    ├── 3_Finance.py         # Finance 2026
    ├── 4_Team.py            # Teams + bonus calculator
    ├── 5_Operations.py      # Operational activities
    └── 9_Debug.py           # Raw data diagnostics
```

## Data Sources (Google Sheets)

| Sheet | Purpose |
|---|---|
| `01.PRJ_LIST` | Project registry (master) |
| `02.OPER_LIST` | Operational tasks |
| `03.PRJ_STATUS` | Milestones — planned vs actual |
| `04.PRJ_TEAM` | Team participation matrix |
| `05.PRJ_MONEY_2026` | Finance: budget, planned and actual payments |

## Local Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Google credentials

Create `.streamlit/secrets.toml`:

```toml
GOOGLE_SHEET_ID = "YOUR_SHEET_ID"

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

### 3. Configure users

```bash
cp config.yaml.example config.yaml
```

Generate a bcrypt password hash:

```bash
python -c "import bcrypt; print(bcrypt.hashpw('YOUR_PASSWORD'.encode(), bcrypt.gensalt(12)).decode())"
```

### 4. Run

```bash
streamlit run app.py --server.port 8501
```

Open [http://localhost:8501](http://localhost:8501).

## VPS Deployment (Docker)

### 1. Prepare `.env`

```bash
cp .env.example .env
# Fill in GOOGLE_SHEET_ID and GCP_SERVICE_ACCOUNT_JSON
```

### 2. Prepare `config.yaml`

```bash
cp config.yaml.example config.yaml
# Fill in users and cookie key
```

### 3. Start the container

```bash
docker-compose up -d --build
```

## Data Refresh

- **Automatic** — every 5 minutes (`@st.cache_data` TTL)
- **Manual** — click **🔄 Refresh data** in the sidebar (clears the full cache)

## Configuration Files

| File | In git | Purpose |
|---|---|---|
| `config.yaml` | ❌ | Users + cookie secret key |
| `config.yaml.example` | ✅ | Template for new deployments |
| `.env` | ❌ | Docker secrets (Sheet ID + SA JSON) |
| `.env.example` | ✅ | .env template |
| `.streamlit/secrets.toml` | ❌ | Local run secrets |

## Security

- Passwords are stored only as bcrypt hashes (12 salt rounds)
- Google Service Account private key is kept only in `.env` and `secrets.toml`, both excluded via `.gitignore`
- Cookie sessions are signed with the secret key from `config.yaml`

## License

[MIT](LICENSE)
