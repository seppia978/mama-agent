# 🍝 MAMA Virtual Waiter

**Cameriere virtuale intelligente** per ristoranti, alimentato da GPT-4o.

Un'esperienza conversazionale naturale per esplorare il menu, ricevere consigli personalizzati e completare l'ordinazione.

## ✨ Caratteristiche

- **Conversazione Naturale**: Dialoga con il cliente come un vero cameriere
- **Suggerimenti Personalizzati**: Propone piatti basandosi su preferenze e restrizioni
- **Gestione Allergie**: Traccia allergie e intolleranze per filtrare suggerimenti
- **Abbinamenti Intelligenti**: Suggerisce combinazioni di piatti e bevande
- **Ordine in Tempo Reale**: Visualizza e modifica l'ordine durante la conversazione

## 🚀 Quick Start

### 1. Installa le dipendenze

```bash
pip install -r requirements.txt
```

### 2. Configura la API key

Crea un file `.env`:

```
OPENAI_API_KEY=sk-your-key-here
```

### 3. Avvia l'applicazione

```bash
streamlit run app.py
```

L'app si aprirà nel browser all'indirizzo `http://localhost:8501`

## 📁 Struttura Progetto

```
mama_agent/
├── app.py                  # Applicazione Streamlit principale
├── src/
│   ├── agents/
│   │   └── waiter.py       # WaiterAgent - cameriere intelligente
│   ├── core/
│   │   └── llm.py          # Provider LLM (GPT-4o)
│   └── services/
│       ├── menu.py         # MenuService - gestione menu
│       └── order.py        # OrderManager - gestione ordini
├── data/
│   └── menu.json           # Menu del ristorante
├── tests/                  # Test suite
├── legacy/                 # Codice precedente (backup)
└── requirements.txt
```

## 🎯 Flusso Cliente

### 1. Esplorazione Menu
```
👤 "Cosa avete di vegetariano?"
🧑‍🍳 "Abbiamo diverse opzioni vegetariane! Ti consiglio..."
```

### 2. Richiesta Consigli
```
👤 "Sono diabetico, cosa mi suggerisci?"
🧑‍🍳 "Capisco, ecco alcune opzioni adatte..."
```

### 3. Ordinazione
```
👤 "Prendo il risotto"
🧑‍🍳 "Ottima scelta! Ho aggiunto il Risotto all'ordine..."
```

### 4. Modifiche
```
👤 "Togli il risotto e metti la pasta"
🧑‍🍳 "Fatto! Ho sostituito il risotto con la pasta..."
```

## 🔧 Personalizzazione

### Menu

Modifica `data/menu.json` per il tuo ristorante:

```json
{
  "ristorante": "Nome Ristorante",
  "sezioni": [
    {
      "nome": "Antipasti",
      "voci": [
        {
          "nome": "Caprese",
          "prezzo": 8.50,
          "descrizione": "Mozzarella e pomodori",
          "allergeni": [7]
        }
      ]
    }
  ],
  "allergeni_legend": {
    "7": "Latte/lattosio"
  }
}
```

### Comportamento Cameriere

Modifica il system prompt in `src/agents/waiter.py` per personalizzare:
- Tono e stile di comunicazione
- Strategia di suggerimenti
- Livello di proattività

## 📊 Architettura

```
┌─────────────┐     ┌─────────────┐
│   Streamlit │────▶│ WaiterAgent │
│     UI      │     │   (GPT-4o)  │
└─────────────┘     └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │  Menu    │ │  Order   │ │   LLM    │
        │ Service  │ │ Manager  │ │ Provider │
        └──────────┘ └──────────┘ └──────────┘
```

- **WaiterAgent**: Orchestratore principale, gestisce conversazione e logica
- **MenuService**: Carica e ricerca nel menu
- **OrderManager**: Gestisce l'ordine corrente e preferenze cliente
- **LLMProvider**: Interfaccia con GPT-4o per generazione risposte

## 🔒 Sicurezza

- La API key è gestita tramite variabili d'ambiente
- Nessun dato sensibile viene loggato
- Le conversazioni non vengono salvate permanentemente

## 📝 Requisiti

- Python 3.9+
- OpenAI API Key (GPT-4o)
- ~100MB RAM

## 🤝 Contributi

Contributi benvenuti! Per favore:
1. Fork il repository
2. Crea un branch per la tua feature
3. Apri una Pull Request

## 📄 Licenza

MIT License

---

**Buon appetito!** 🍝
