# 🌐 Настройка GitHub Pages для Web App

## 📋 Что нужно сделать:

### 1. Создай новый репозиторий на GitHub
1. Открой https://github.com/new
2. Название: **StarPayUzWebApp**
3. Описание: **Web App pages for StarPayUz bot**
4. **Public** ✅ (обязательно для GitHub Pages!)
5. ❌ НЕ добавляй README, .gitignore, license
6. Нажми **Create repository**

### 2. Выполни команды на компьютере

Открой CMD или PowerShell и выполни:

```cmd
cd D:\StarPayUzAuto\webapp
git init
git add .
git commit -m "Initial commit - Web App pages"
git branch -M main
git remote add origin https://github.com/Kamron5505/StarPayUzWebApp.git
git push -u origin main
```

### 3. Включи GitHub Pages

1. Открой репозиторий: https://github.com/Kamron5505/StarPayUzWebApp
2. Нажми **Settings** (вкладка сверху)
3. В левом меню найди **Pages**
4. В секции **Build and deployment**:
   - **Source**: Deploy from a branch
   - **Branch**: `main` → папка `/ (root)`
   - Нажми **Save**
5. Подожди 1-2 минуты

### 4. Получи URL

GitHub Pages будет доступен по адресу:
```
https://kamron5505.github.io/StarPayUzWebApp/
```

Проверь что страницы работают:
- https://kamron5505.github.io/StarPayUzWebApp/stars.html ✅
- https://kamron5505.github.io/StarPayUzWebApp/premium.html ✅

### 5. Обнови WEBAPP_URL в Railway

1. Открой Railway → Твой проект
2. Вкладка **Variables**
3. Найди **WEBAPP_URL**
4. Измени на: `https://kamron5505.github.io/StarPayUzWebApp`
5. Сохрани (Railway автоматически перезапустится)

## ✅ Готово!

Теперь кнопки в боте будут открывать Web App с GitHub Pages!

---

## 🔄 Если нужно обновить Web App в будущем:

```cmd
cd D:\StarPayUzAuto\webapp
git add .
git commit -m "Update Web App"
git push
```

GitHub Pages обновится автоматически через 1-2 минуты!
