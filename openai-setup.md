# Konfiguracja OpenAI API dla Aplikacji Sills

## Opis
Aplikacja Sills może analizować kontrakty i dokumenty używając OpenAI API. Aby włączyć tę funkcjonalność, musisz skonfigurować klucz API.

## Jak uzyskać klucz OpenAI API

1. **Przejdź do**: https://platform.openai.com/api-keys
2. **Zaloguj się** lub utwórz konto
3. **Utwórz nowy klucz API**
4. **Skopiuj klucz** (będzie wyglądał jak: `sk-...`)

## Sposoby konfiguracji klucza API

### Metoda 1: Zmienna środowiskowa (Windows)
```cmd
set OPENAI_API_KEY=sk-your-api-key-here
python app.py
```

### Metoda 2: Zmienna środowiskowa (Linux/Mac)
```bash
export OPENAI_API_KEY=sk-your-api-key-here
python app.py
```

### Metoda 3: Argument wiersza poleceń
```bash
python app.py --openai-key sk-your-api-key-here
```

### Metoda 4: Plik .env (najlepsza opcja)
1. Utwórz plik `.env` w katalogu głównym aplikacji
2. Dodaj linię:
```env
OPENAI_API_KEY=sk-your-api-key-here
```
3. Uruchom aplikację: `python app.py`

### Metoda 5: Dla Colify
Dodaj zmienną środowiskową w panelu Colify:
- **Nazwa**: `OPENAI_API_KEY`
- **Wartość**: `sk-your-api-key-here`

## Sprawdzenie czy klucz działa

Po uruchomieniu aplikacji z kluczem API, w logach zobaczysz:
```
OpenAI API key is available - contract analysis enabled
```

## Funkcjonalności wymagające OpenAI API

- **Analiza kontraktów** - automatyczne wyciąganie danych z dokumentów
- **OCR dokumentów** - rozpoznawanie tekstu z obrazów
- **Inteligentne parsowanie** - automatyczne wypełnianie formularzy

## Bezpieczeństwo

- **Nigdy nie commit-uj** klucza API do repozytorium
- **Używaj zmiennych środowiskowych** w produkcji
- **Klucz jest maskowany** w logach (pokazuje tylko początek i koniec)

## Koszty

OpenAI API jest płatne. Koszty zależą od:
- Ilości analizowanych dokumentów
- Rozmiaru dokumentów
- Używanego modelu

Szacowany koszt: ~$0.01-0.10 za dokument