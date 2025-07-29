# Instrukcja Instalacji na Colify - Aplikacja Sills

## Opis Aplikacji
Aplikacja Sills to system zarządzania parapetami okiennymi napisany w Flask, który umożliwia:
- Zarządzanie klientami
- Zarządzanie zamówieniami parapetów
- Kalkulację materiałów i kosztów
- Analizę kontraktów (z OpenAI API)
- Generowanie raportów

## Wymagania Systemowe
- Python 3.11+ (zgodnie z Dockerfile)
- SQLite (wbudowana baza danych)
- 512MB RAM minimum
- 1GB miejsca na dysku

## Zmienne Środowiskowe dla Colify - PRAWDZIWE DANE

### Wymagane Zmienne:
```env
SECRET_KEY=your-secret-key
FLASK_ENV=production
FLASK_DEBUG=False
DATABASE_URL=sqlite:///sills.db
SQLALCHEMY_TRACK_MODIFICATIONS=False
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216
ALLOWED_EXTENSIONS=png,jpg,jpeg,gif,pdf
RATELIMIT_DEFAULT=200 per day
RATELIMIT_STORAGE_URL=memory://
PORT=56666
HOST=0.0.0.0
FLASK_APP=app.py
PYTHONPATH=/app
```

### OpenAI API (Dla analizy kontraktów):
```env
OPENAI_API_KEY=your-openai-api-key-here
```

## Instalacja na Colify

### Krok 1: Dodaj Repozytorium
1. W panelu Colify kliknij "New Service"
2. Wybierz "Application"
3. Podłącz swoje repozytorium GitHub: `https://github.com/TomBelfast/sills2`
4. Wybierz branch: `main`

### Krok 2: Konfiguracja Build
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python app.py`
- **Port**: `56666`

### Krok 3: Zmienne Środowiskowe
Skopiuj wszystkie zmienne z sekcji "Zmienne Środowiskowe" powyżej do panelu Colify.

**WAŻNE**: Dla funkcji analizy kontraktów musisz dodać swój klucz OpenAI API:
1. Przejdź do https://platform.openai.com/api-keys
2. Utwórz nowy klucz API
3. Skopiuj klucz i wklej jako wartość `OPENAI_API_KEY` w Colify

### Krok 4: Deployment
1. Kliknij "Deploy"
2. Poczekaj na zakończenie build i start
3. Sprawdź logi czy aplikacja uruchomiła się poprawnie

## Funkcjonalności Aplikacji

### ✅ Działające Funkcje:
- **Zarządzanie Klientami**: Dodawanie, edycja, usuwanie klientów
- **Zarządzanie Parapetami**: Dodawanie, edycja, usuwanie parapetów
- **Kalkulacja Materiałów**: Automatyczne obliczanie potrzebnych materiałów
- **Kalkulacja Cen**: Obliczanie kosztów na podstawie materiałów i cen
- **Analiza Kontraktów**: Automatyczne parsowanie plików PDF z OpenAI API
- **Generowanie Raportów**: Eksport danych do różnych formatów

### 🔧 Naprawione Problemy:
- ✅ Błąd `Client.__init__() got an unexpected keyword argument 'proxies'`
- ✅ Obsługa klucza OpenAI API
- ✅ Automatyczna inicjalizacja bazy danych
- ✅ Kodowanie UTF-8 w logach
- ✅ Walidacja danych wejściowych

## Monitoring i Logi

### Sprawdzanie Statusu:
- **Health Check**: `http://your-domain:56666/`
- **Logi**: Sprawdź logi aplikacji w panelu Colify

### Typowe Problemy:
- **Port 56666**: Upewnij się, że port jest otwarty w Colify
- **Baza danych**: SQLite jest wbudowana, nie wymaga dodatkowej konfiguracji
- **OpenAI API**: Sprawdź czy klucz API jest poprawny

## Bezpieczeństwo

### ✅ Zaimplementowane Zabezpieczenia:
- Walidacja danych wejściowych
- Sanityzacja danych wyjściowych
- Bezpieczne przesyłanie plików
- Rate limiting (200 requestów dziennie)
- Logowanie błędów

### 🔒 Rekomendacje:
- Zmień `SECRET_KEY` na unikalny klucz
- Używaj HTTPS w produkcji
- Regularnie aktualizuj zależności

## Wsparcie

### Dokumentacja:
- **GitHub**: https://github.com/TomBelfast/sills2
- **Issues**: Zgłaszaj problemy na GitHub

### Funkcje:
1. **Zarządzanie klientami** (`/clients`)
2. **Zarządzanie parapetami** (`/sills`)
3. **Kalkulacja materiałów** (`/materials`)
4. **Kalkulacja cen** (`/price`)
5. **Ustawienia systemu** (`/settings`)
6. **Analiza kontraktów** (`/upload_contract`)

---

**Aplikacja Sills jest gotowa do deployment na Colify!** 🚀