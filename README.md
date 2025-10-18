# 🍝 Cameriere Virtuale - Virtual Waiter Agent

Sistema agente intelligente che simula un cameriere per aiutare i clienti di un ristorante nella scelta dell'ordinazione. Il sistema utilizza Llama-3.1-8B-Instruct per generare conversazioni naturali e personalizzate.

## Caratteristiche

- **Conversazione Naturale**: Dialoga con il cliente come un vero cameriere
- **Suggerimenti Personalizzati**: Propone piatti basandosi sulle preferenze del cliente
- **Gestione Allergie**: Tiene traccia di allergie e restrizioni alimentari
- **Abbinamenti Intelligenti**: Suggerisce combinazioni di piatti e bevande
- **Gestione Ordini**: Traccia l'ordine corrente e calcola il totale
- **Multi-Provider LLM**: Supporta diversi provider (Ollama, HuggingFace, OpenAI-compatible)

## Architettura

```
mama_agent/
├── main.py              # Applicazione principale con CLI
├── waiter_agent.py      # Logica del cameriere agente
├── llm_provider.py      # Integrazione con LLM (multi-provider)
├── menu.json            # Menu del ristorante (esempio)
└── requirements.txt     # Dipendenze Python
```

### Componenti

1. **LLM Provider** ([llm_provider.py](llm_provider.py))
   - Astrazione per diversi provider LLM
   - Supporta: Ollama, HuggingFace Transformers, API OpenAI-compatible

2. **Waiter Agent** ([waiter_agent.py](waiter_agent.py))
   - Logica conversazionale del cameriere
   - Gestione ordini e preferenze
   - Ricerca e suggerimenti nel menu

3. **Main Application** ([main.py](main.py))
   - Interfaccia CLI interattiva
   - Gestione comandi speciali

## Installazione

### 1. Clona e installa le dipendenze

```bash
cd mama_agent
pip install -r requirements.txt
```

### 2. Scegli e configura il provider LLM

#### Opzione A: Ollama (Consigliato - Più Facile)

Ollama è il metodo più semplice per eseguire Llama localmente.

```bash
# Installa Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Avvia il server Ollama
ollama serve

# In un altro terminale, scarica il modello
ollama pull llama3.1:8b-instruct-q4_K_M
```

#### Opzione B: HuggingFace Transformers (Locale)

Per eseguire il modello direttamente con PyTorch:

```bash
# Assicurati di avere PyTorch installato
pip install torch torchvision torchaudio

# Login su Hugging Face (richiede token)
huggingface-cli login

# Accetta i termini di Llama su: https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct
```

#### Opzione C: OpenAI-Compatible API

Per servizi come vLLM, LM Studio, o altri server compatibili con OpenAI:

```bash
# Esempio con vLLM
pip install vllm
vllm serve meta-llama/Llama-3.1-8B-Instruct --port 8000
```

## Utilizzo

### Modalità Interattiva (CLI)

```bash
# Con Ollama (default)
python main.py

# Con HuggingFace
python main.py --provider huggingface

# Con API OpenAI-compatible
python main.py --provider openai_compatible --base-url http://localhost:8000/v1

# Con menu personalizzato
python main.py --menu il_mio_menu.json
```

### Comandi Speciali

Durante la conversazione, puoi usare questi comandi:

- `menu` - Visualizza il menu completo
- `ordine` - Mostra l'ordine corrente
- `reset` - Azzera l'ordine e ricomincia
- `esci` o `quit` - Termina la conversazione

### Esempio di Conversazione

```
🧑‍🍳 Cameriere: Buonasera! Benvenuto da Mama's Trattoria!
              Come posso aiutarla oggi? Ha già un'idea di cosa desidera?

👤 Tu: Ciao! Sono vegetariano, cosa mi consiglia?

🧑‍🍳 Cameriere: Perfetto! Abbiamo diverse ottime opzioni vegetariane.
              Le consiglio di iniziare con la nostra Caprese, fatta con
              mozzarella di bufala campana DOP freschissima. Come primo,
              il Risotto ai Funghi Porcini è spettacolare - i funghi sono
              freschi del bosco! Oppure se preferisce qualcosa di più
              semplice, le Penne all'Arrabbiata sono anche vegane.
              Cosa ne dice?

👤 Tu: Ottimo! Prendo la caprese e il risotto

🧑‍🍳 Cameriere: Eccellente scelta! Caprese e Risotto ai Funghi Porcini -
              vedrà che combinazione perfetta! Posso suggerirle un buon
              vino bianco per accompagnare? Il nostro vino della casa
              bianco si abbina perfettamente con questi piatti.

👤 Tu: ordine

📝 Il tuo ordine:
- Caprese x1 (8.50€)
- Risotto ai Funghi Porcini x1 (13.50€)

Totale: 22.00€
```

## Personalizzazione

### Modificare il Menu

Modifica il file [menu.json](menu.json) seguendo questa struttura:

```json
{
  "ristorante": "Nome Ristorante",
  "categorie": {
    "antipasti": [
      {
        "id": "ant_001",
        "nome": "Nome Piatto",
        "descrizione": "Descrizione dettagliata",
        "prezzo": 10.00,
        "allergeni": ["glutine", "lattosio"],
        "vegetariano": true,
        "vegano": false,
        "suggerimenti": "Messaggio persuasivo per il cameriere"
      }
    ]
  }
}
```

### Personalizzare il Comportamento del Cameriere

Modifica il `system_prompt` in [waiter_agent.py:81](waiter_agent.py#L81) per cambiare:
- Tono e personalità
- Stile di suggerimenti
- Livello di proattività
- Formattazione delle risposte

### Integrare Altri LLM

Aggiungi nuovi provider in [llm_provider.py](llm_provider.py) implementando la classe `LLMProvider`:

```python
class MyCustomProvider(LLMProvider):
    def generate(self, messages: List[Dict[str, str]],
                 max_tokens: int = 512,
                 temperature: float = 0.7) -> str:
        # La tua implementazione
        pass
```

## Requisiti di Sistema

### Minimi (con Ollama)
- RAM: 8 GB
- Storage: 5 GB (per il modello)
- CPU: Multi-core moderno

### Consigliati (con GPU)
- RAM: 16 GB
- GPU: 6 GB VRAM (per HuggingFace/vLLM)
- Storage: 20 GB

## Funzionalità Avanzate

### Tracking delle Preferenze

Il sistema traccia automaticamente:
- Preferenze vegetariane/vegane
- Allergie alimentari
- Preferenze sul piccante
- Budget (se menzionato)

### Ricerca nel Menu

```python
from waiter_agent import WaiterAgent

# Cerca piatti vegetariani sotto 10€
results = agent.search_menu(
    query="pasta",
    filters={
        "vegetarian": True,
        "max_price": 10.0
    }
)
```

### Export Conversazione

```python
# Salva la conversazione
history = agent.get_conversation_history()
with open("conversazione.json", "w") as f:
    json.dump(history, f, indent=2)
```

## Troubleshooting

### Ollama non si connette
```bash
# Verifica che Ollama sia in esecuzione
curl http://localhost:11434/api/tags

# Riavvia Ollama
ollama serve
```

### Errore memoria insufficiente
```bash
# Usa un modello quantizzato più piccolo
ollama pull llama3.1:8b-instruct-q4_0  # Più compresso
```

### Risposte lente
- Usa Ollama con quantizzazione Q4
- Considera l'uso di una GPU
- Riduci `max_tokens` in [waiter_agent.py:154](waiter_agent.py#L154)

## Sviluppi Futuri

- [ ] Interfaccia web con FastAPI
- [ ] Supporto multi-lingua
- [ ] Integrazione con sistema di pagamento
- [ ] Voice interface (STT/TTS)
- [ ] Analytics sugli ordini
- [ ] Sistema di feedback clienti
- [ ] Integrazione con sistema di cucina

## Licenza

MIT License - Libero per uso commerciale e personale

## Contributi

Contributi benvenuti! Apri una issue o una pull request.

## Contatti

Per domande o supporto, apri una issue su GitHub.

---

Buon appetito! 🍝
