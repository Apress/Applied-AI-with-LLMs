# News Aggregator MVP

Script minimale che recupera le ultime notizie tramite NewsAPI, le comprime con Google Gemini in frasi da massimo 20 parole e le stampa nel terminale.

## Requisiti
- Python 3.10+
- Credenziali per:
  - [NewsAPI](https://newsapi.org/)
  - [Google AI Studio](https://aistudio.google.com/) (chiave Gemini)

## Setup

1. **Clona il repository e naviga nella directory del progetto**

2. **Crea ed attiva un virtual environment** (opzionale ma consigliato):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Su Windows: venv\Scripts\activate
   ```

3. **Installa le dipendenze**:
   ```bash
   pip install -r requirements.txt
   ```
   
   Oppure manualmente:
   ```bash
   pip install requests>=2.31.0 python-dotenv>=1.0.0 google-genai>=1.0.0
   ```

4. **Configura le variabili d'ambiente**:
   - Copia il file `.env.example` in `.env`:
     ```bash
     cp .env.example .env
     ```
   - Modifica `.env` inserendo le tue chiavi API:
     ```bash
     NEWS_API_KEY=your_newsapi_key_here
     GEMINI_API_KEY=your_gemini_api_key_here
     GEMINI_MODEL=gemini-2.5-flash
     MAX_WORDS=20
     PROMPT_FILE_PATH=prompts/prompt_template.txt
     ```

## Variabili d'Ambiente

- `NEWS_API_KEY` (obbligatoria): Chiave API per NewsAPI
- `GEMINI_API_KEY` (obbligatoria): Chiave API per Google Gemini
- `GEMINI_MODEL` (opzionale): Modello Gemini da usare (default: `gemini-pro`)
- `MAX_WORDS` (opzionale): Numero massimo di parole per riassunto (default: `20`)
- `PROMPT_FILE_PATH` (opzionale): Percorso del file prompt template (default: `prompts/prompt_template.txt`)

## Esecuzione

```bash
python3 script.py
```

Il programma:
1. Recupera le headline da NewsAPI
2. Per ogni articolo, chiede a Gemini di comprimerlo in una frase
3. Stampa i riassunti nel terminale con logging delle operazioni

## Funzionalità

- ✅ Recupero notizie da NewsAPI
- ✅ Compressione articoli con Google Gemini AI
- ✅ Logging delle operazioni
- ✅ Gestione errori con try-except
- ✅ Configurazione tramite file `.env`
- ✅ Prompt template personalizzabile

## Personalizzazione

- **Prompt template**: Modifica `prompts/prompt_template.txt` per cambiare come vengono generati i riassunti
- **Numero di parole**: Modifica `MAX_WORDS` nel file `.env`
- **Modello AI**: Cambia `GEMINI_MODEL` nel file `.env` (es: `gemini-2.5-flash`, `gemini-pro`)

## Note

- Il progetto è volutamente riunito in un singolo file (`script.py`) come da requisiti MVP
- Le credenziali non vanno versionate: `.env` è già in `.gitignore`
- Il logging è configurato a livello INFO e mostra lo stato delle operazioni
- Gli errori vengono gestiti gracefully: se un articolo fallisce, il programma continua con i successivi

