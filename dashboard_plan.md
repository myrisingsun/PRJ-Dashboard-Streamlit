# План разработки: Project Portfolio Dashboard (Streamlit)

## Источник данных

**Google Sheets ID:** `1gL4m-sOtleIwL7di24KEwK5onJBUmj5w`

Файл содержит 7 листов:

| Лист | Назначение |
|------|-----------|
| `01.PRJ_LIST` | Реестр проектов: код, название, статус, ссылки, сроки |
| `02.OPER_LIST` | Внепроектная / операционная работа |
| `03.PRJ_STATUS` | Статусы по месяцам 2025–2027, план/факт, ключевые точки (Гант) |
| `04.PRJ_TEAM` | Команды проектов: ФИО, роли (A/S/БА), количество участников |
| `05.PRJ_MONEY_2026` | Финансы: бюджет 2026, план/факт по месяцам, документы оплат |
| `СВОД` | Сводный лист (пока пустой — зарезервировать) |
| `DATA` | Справочники (пока пустой — зарезервировать) |

---

## Маппинг статусов → цвета

```python
STATUS_COLORS = {
    "По плану":      "#2ECC71",  # зелёный
    "Есть риски":    "#E74C3C",  # красный
    "Приостановлен": "#95A5A6",  # серый
    "Отстает":       "#F1C40F",  # жёлтый
}
```

Источник статуса: `01.PRJ_LIST`, колонка `Текущий статус` (col index 11, row начало с row 3).

---

## Архитектура приложения

```
dashboard/
├── app.py                  # точка входа, роутинг страниц
├── auth.py                 # аутентификация (streamlit-authenticator)
├── data/
│   └── loader.py           # загрузка и кэш данных из Google Sheets
├── pages/
│   ├── 1_Index.py          # Главная — портфель
│   ├── 2_Gantt.py          # Статус и диаграмма Ганта
│   ├── 3_Finance.py        # Финансы по проектам
│   ├── 4_Team.py           # Команды и премии
│   └── 5_Operations.py     # Внепроектная работа
├── components/
│   ├── status_badge.py     # цветной маркер статуса
│   ├── gantt_chart.py      # Plotly Gantt
│   └── finance_table.py    # таблица финансов
├── config.yaml             # логины/пароли (streamlit-authenticator)
├── requirements.txt
└── .streamlit/
    └── secrets.toml        # GOOGLE_SHEET_ID, SERVICE_ACCOUNT_JSON
```

---

## Стек технологий

| Компонент | Библиотека / Сервис |
|-----------|-------------------|
| UI фреймворк | `streamlit >= 1.35` |
| Аутентификация | `streamlit-authenticator` |
| Google Sheets | `gspread` + Google Service Account |
| Кэширование данных | `@st.cache_data(ttl=300)` — обновление каждые 5 мин |
| Графики | `plotly` (Gantt, Bar, Pie) |
| Таблицы | `st.dataframe` + `pandas` |
| Деплой | Streamlit Community Cloud (бесплатно) или Docker + VPS |

---

## Модуль загрузки данных (`data/loader.py`)

```python
import gspread, pandas as pd, streamlit as st
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

@st.cache_data(ttl=300)  # кэш 5 минут — данные свежие после правок в таблице
def load_sheet(sheet_name: str) -> pd.DataFrame:
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(st.secrets["GOOGLE_SHEET_ID"])
    ws = sh.worksheet(sheet_name)
    data = ws.get_all_values()
    # Для каждого листа — свой парсер заголовков (см. ниже)
    return data
```

**Почему `ttl=300`:** при сохранении таблицы данные появятся в дашборде максимум через 5 минут без перезапуска приложения. Можно сократить до `ttl=60`.

---

## Парсеры листов

### `01.PRJ_LIST` → `parse_prj_list(data)`
- Заголовок на строке 3 (0-index: 2)
- Ключевые колонки:
  - `Код проекта` — уникальный ключ
  - `Сокращенное название проекта`
  - `Текущий статус` → маппинг цветов
  - `Плановый срок` → парсить диапазон `Q1 2024 - Q2 2026`
  - `Ссылка на систему PROD` / `Ссылка на приказ в Bitrix24 (PDF)`

### `03.PRJ_STATUS` → `parse_prj_status(data)`
- Сложная многоуровневая шапка: строки 1–3 содержат год / квартал / месяц
- Нужно собрать MultiIndex колонок: `(год, месяц)`
- Строки бывают двух типов: `Plan` и `Fact` — разделять по колонке `План \ Факт` (col 4)
- Значение `1` в ячейке = ключевая точка достигнута
- Из диапазона `Срок` (col 6) парсить `start_date` / `end_date` для Ганта

### `04.PRJ_TEAM` → `parse_prj_team(data)`
- Заголовок строка 3: ФИО сотрудников как названия колонок
- Строка 2: должности
- Значения ячеек: `A` (РП), `S` (участник), `БА` (бизнес-аналитик), `None`
- В конце каждой строки есть числовое значение (кол-во человек в проекте)
- Для модуля премий: матрица участия `project × person`

### `05.PRJ_MONEY_2026` → `parse_prj_money(data)`
- Сложная структура: строки группируются по IT-продуктам (LITE BIM, PLAN R, и т.д.)
- Каждая группа: `название продукта` → строки с позициями → строка `Итого помесячно`
- Колонки: `Бюджет 2026`, затем `план/факт` по каждому месяцу (12×2 = 24 col)
- Итоговые колонки: `План оплат`, `Факт оплат`, `Отклонение`, `Запланировано но не оплачено`

---

## Страницы

### Страница 1: Index — Портфель проектов

**Верхний блок — KPI-карточки (4 метрики):**
```
[Всего проектов: 13] [Бюджет 2026: X млн] [Факт оплат: Y млн] [Исполнение: Z%]
```

**Средний блок — сводная таблица проектов:**

| # | Код | Название | Срок | Статус 🟢🔴🟡⚫ | Бюджет | Факт | Осталось | Bitrix | PROD |
|---|-----|----------|------|----------------|--------|------|----------|--------|------|

Реализация статусного маркера:
```python
# в st.dataframe через column_config или через HTML в st.markdown
def status_emoji(status):
    return {"По плану": "🟢", "Есть риски": "🔴",
            "Приостановлен": "⚫", "Отстает": "🟡"}.get(status, "⚪")
```

**Нижний блок — диаграммы:**
- Pie chart: распределение проектов по статусам
- Bar chart: бюджет vs факт по проектам (горизонтальный)

---

### Страница 2: Гант и статус выполнения

**Фильтр:** выбор проекта (selectbox) или показать все

**Диаграмма Ганта (Plotly Timeline):**
```python
import plotly.express as px
fig = px.timeline(
    df,
    x_start="start_date",
    x_end="end_date",
    y="project_code",
    color="status",
    color_discrete_map=STATUS_COLORS
)
```

**Ключевые точки (milestones):**
- Данные из `03.PRJ_STATUS`: где значение = `1` в ячейке месяца
- Отображать как маркеры (◆) поверх Ганта
- Рядом показывать: `название точки`, `план vs факт`

**Таблица план/факт:**
- Для выбранного проекта: по строкам — ключевые точки, по колонкам — месяцы
- Цветовая подсветка: факт ≥ план → зелёный, факт < план → красный

---

### Страница 3: Финансы

**Фильтры:** год (2026), проект / IT-продукт, месяц

**KPI:**
```
[Бюджет 2026: X] [Оплачено: Y] [Отклонение: Z] [Не оплачено: W]
```

**График — waterfall или stacked bar:**
- По оси X: месяцы
- По оси Y: план (синий) / факт (зелёный)
- Если факт > план — красный

**Детальная таблица по позициям:**

| IT-продукт | Позиция | Бюджет | Янв план | Янв факт | ... | Итого факт | Отклонение |
|------------|---------|--------|----------|----------|-----|------------|------------|

**Документы оплат — через комментарии Google Sheets:**
- При загрузке листа `05.PRJ_MONEY_2026` через `gspread` дополнительно вызывать `worksheet.get_all_values()` + `batch_get` с флагом `includeGridData=True` через Sheets API v4 напрямую
- Из ответа извлекать `sheets[0].data[0].rowData[i].values[j].note` — это текст комментария ячейки
- Показывать в таблице: если у ячейки факта есть `note` → иконка 📎 + tooltip / expander со ссылкой на документ
- Альтернатива проще: `gspread` метод `cell.note` через `ws.cell(row, col).note`

---

### Страница 4: Команды и премии

**Матрица участия:**
- По строкам — проекты
- По колонкам — сотрудники
- Ячейки: `A` / `S` / `БА` с цветовой подсветкой роли

**Сводка по сотруднику:**
- selectbox → выбрать сотрудника
- показать: в каких проектах участвует, роль, количество проектов

**Модуль распределения премии:**
```
Общий фонд премии: [input поле, руб.]

Метод распределения:
○ Поровну по участникам
○ С весом по роли (A = 3x, БА = 2x, S = 1x)
○ С весом по количеству проектов

→ [Рассчитать]

Результат: таблица ФИО → сумма премии
→ [Скачать CSV]
```

---

### Страница 5: Внепроектная работа

Данные из `02.OPER_LIST`:
- Список операционных задач (КОД ИИ, Оперативные отчеты, Электронный архив, Дизайн-проекты, СИЗы, и др.)
- Аналогичная структура: статус, ответственный, ссылки
- Упрощённая версия страницы 1 без финансов

---

## Аутентификация (`auth.py`)

Использовать `streamlit-authenticator`:

```yaml
# config.yaml
credentials:
  usernames:
    admin:
      name: Администратор
      password: $2b$12$...  # bcrypt hash
    user1:
      name: Пахарев К.А.
      password: $2b$12$...
cookie:
  expiry_days: 7
  key: dashboard_secret_key
  name: afi_dashboard
```

```python
# app.py
import streamlit as st
import streamlit_authenticator as stauth
import yaml

with open("config.yaml") as f:
    config = yaml.safe_load(f)

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

name, authentication_status, username = authenticator.login("Вход", "main")

# ВСЕ страницы недоступны без авторизации — рендер только после проверки
if authentication_status is False:
    st.error("Неверный логин или пароль")
    st.stop()  # дальше ничего не рендерится
elif authentication_status is None:
    st.warning("Введите логин и пароль")
    st.stop()  # дальше ничего не рендерится
elif authentication_status:
    authenticator.logout("Выйти", "sidebar")
    st.sidebar.write(f"👤 {name}")
    # → только здесь рендер страниц
```

**Управление пользователями** — редактировать `config.yaml` на VPS, затем `docker-compose restart`:

```yaml
# config.yaml
credentials:
  usernames:
    pakharev:
      name: Пахарев К.А.
      password: $2b$12$...  # bcrypt hash
    valyaychikov:
      name: Валяйчиков А.В.
      password: $2b$12$...
cookie:
  expiry_days: 7
  key: afi_dashboard_secret_key_2026
  name: afi_dashboard
```

**Генерация хэша пароля** (выполнить один раз локально):
```python
import bcrypt
print(bcrypt.hashpw("пароль123".encode(), bcrypt.gensalt()).decode())
```

---

## Деплой

### Docker + VPS

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501"]
```

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
```

```yaml
# docker-compose.yml
version: "3.9"
services:
  dashboard:
    build: .
    restart: always
    ports:
      - "8501:8501"
    env_file:
      - .env          # GOOGLE_SHEET_ID + GCP_SERVICE_ACCOUNT_JSON
    volumes:
      - ./config.yaml:/app/config.yaml:ro   # логины/пароли — не в образе
```

**Обновление данных:** `ttl=300` в `@st.cache_data` — без перезапуска контейнера.  
**Обновление кода:** `git pull && docker-compose up -d --build`  
**Nginx reverse proxy** (опционально, для HTTPS):
```nginx
location / {
    proxy_pass http://localhost:8501;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}
```

---

## Google Service Account (настройка доступа)

1. Google Cloud Console → создать проект
2. APIs & Services → включить **Google Sheets API**
3. Credentials → Create Service Account → скачать JSON ключ
4. В Google Sheets → Поделиться → добавить email сервисного аккаунта как **Читатель**

---

## requirements.txt

```
streamlit>=1.35.0
streamlit-authenticator>=0.3.2
gspread>=6.0.0
google-auth>=2.28.0
pandas>=2.0.0
plotly>=5.18.0
pyyaml>=6.0
bcrypt>=4.1.0
openpyxl>=3.1.0
```

---

## Порядок разработки (рекомендуемые шаги для Claude Code)

1. **Шаг 1:** Создать `data/loader.py` — подключение к Google Sheets, парсеры всех 5 листов, тесты на реальных данных
2. **Шаг 2:** `auth.py` + `config.yaml` — аутентификация, создание хэшей паролей
3. **Шаг 3:** `app.py` — роутинг, проверка авторизации, sidebar навигация
4. **Шаг 4:** `pages/1_Index.py` — главная страница с KPI и таблицей
5. **Шаг 5:** `pages/2_Gantt.py` — Plotly Timeline + ключевые точки
6. **Шаг 6:** `pages/3_Finance.py` — финансовые графики и таблица
7. **Шаг 7:** `pages/4_Team.py` — матрица + калькулятор премий
8. **Шаг 8:** `pages/5_Operations.py` — операционная работа
9. **Шаг 9:** Деплой на Streamlit Community Cloud
