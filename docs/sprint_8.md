# Sprint 8 — Результаты

## 1. Разграничение прав доступа (роли)

### Новый пользователь — `viewer`

| Логин | Пароль | Роль | Доступные страницы |
|-------|--------|------|--------------------|
| `viewer` | `viewer2026` | viewer | Gantt, Team |
| `admin` / `pakharev` | без изменений | admin | все страницы |

### Реализация

- В `config.yaml` добавлен пользователь `viewer` и секция `roles` (маппинг username → role)
- В `auth.py` добавлены функции:
  - `get_current_role()` — возвращает роль текущего пользователя
  - `require_role(allowed_roles)` — блокирует страницу с сообщением «🚫 Нет доступа» если роль не в списке
- `render_sidebar_user()` — у viewer в сайдбаре отображается пометка `(просмотр)`
- На главной (`app.py`) навигационный список в сайдбаре зависит от роли: viewer видит только Gantt и Team

### Страницы, закрытые для viewer (`require_role(["admin"])`)

- `1_Index.py`
- `3_Finance.py`
- `5_Operations.py`
- `6_Projects.py`
- `7_Motivation.py`
- `9_Debug.py`

---

## 2. Новая страница: 🏆 Motivation

- Калькулятор проектной премии **перенесён** из `4_Team.py` в новый файл `pages/7_Motivation.py`
- Улучшена раскладка: настройки (фонд + метод) — слева, таблица результатов — справа
- Доступна только для роли `admin`
- Три метода распределения: поровну / с весом по роли / с весом по количеству проектов
- Выгрузка результата в CSV, визуализация bar-чартом

---

## 3. Страница Team — упрощение

- Удалена секция «Распределение премии» (перенесена в Motivation)
- Заголовок изменён: «Команды и распределение премий» → «Команды проектов»

---

## 4. Переименование страницы Project → Projects

- Файл `6_Project.py` переименован в `6_Projects.py`
- `page_title` обновлён на `Projects`
- Ссылки на `/Project?project=...` в `1_Index.py` и `4_Team.py` обновлены на `/Projects?project=...`

---

## Файлы изменений

| Файл | Изменения |
|------|-----------|
| `config.yaml` | Новый пользователь `viewer`, секция `roles` |
| `auth.py` | `get_current_role()`, `require_role()`, обновлён `render_sidebar_user()` |
| `app.py` | Навигация зависит от роли, добавлен Motivation в список, обновлена таблица разделов |
| `pages/1_Index.py` | `require_role(["admin"])`, ссылка на `/Projects` |
| `pages/3_Finance.py` | `require_role(["admin"])` |
| `pages/5_Operations.py` | `require_role(["admin"])` |
| `pages/4_Team.py` | Удалён калькулятор премий, новый заголовок, ссылка на `/Projects` |
| `pages/6_Project.py` → `pages/6_Projects.py` | Переименование, обновлён `page_title`, `require_role(["admin"])` |
| `pages/7_Motivation.py` | Новая страница — калькулятор премий |
| `pages/9_Debug.py` | `require_role(["admin"])` |
