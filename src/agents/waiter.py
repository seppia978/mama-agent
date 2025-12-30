"""
Waiter Agent - Cameriere virtuale intelligente
Gestisce l'intera conversazione con il cliente usando GPT-4o
"""
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

from ..core.llm import LLMProvider
from ..services.menu import MenuService
from ..services.order import OrderManager


class ConversationPhase(Enum):
    """Fasi della conversazione"""
    GREETING = "greeting"
    EXPLORING = "exploring"      # Esplorazione menu
    ORDERING = "ordering"        # Ordinazione
    CONFIRMING = "confirming"    # Conferma ordine
    COMPLETED = "completed"


@dataclass
class MessageAnalysis:
    """Risultato dell'analisi del messaggio"""
    is_order: bool
    is_question: bool
    is_modification: bool
    extracted_items: List[Dict]
    preferences_detected: Dict
    needs_clarification: bool
    clarification_reason: str = ""


class WaiterAgent:
    """
    Cameriere virtuale intelligente.
    Unifica le funzionalità di guard, supervisor e waiter in un unico agente.
    """

    def __init__(
        self,
        llm: LLMProvider,
        menu: MenuService,
        order: OrderManager
    ):
        self.llm = llm
        self.menu = menu
        self.order = order
        self.conversation_history: List[Dict[str, str]] = []
        self.phase = ConversationPhase.GREETING

    def _get_system_prompt(self) -> str:
        """Costruisce il system prompt"""
        menu_text = self.menu.format_for_llm()
        preferences = self.order.preferences.format_for_waiter()
        order_summary = self.order.get_summary() if not self.order.is_empty() else ""

        return f"""Sei un cameriere esperto e cordiale del ristorante "{self.menu.get_restaurant_name()}".

PERSONALITA':
- Amichevole, professionale e attento
- Conosci perfettamente il menu
- Dai suggerimenti personalizzati basati sulle preferenze
- Sei proattivo nel proporre abbinamenti
- Gestisci allergie e intolleranze con massima cura
- Rispondi SEMPRE in italiano

{menu_text}

PREFERENZE CLIENTE ATTUALI: {preferences}

{f"ORDINE CORRENTE:{chr(10)}{order_summary}" if order_summary else ""}

REGOLE:
1. Quando il cliente ordina, conferma sempre l'aggiunta
2. Se chiede consigli, proponi 2-3 opzioni con spiegazioni
3. Ricorda sempre allergie e preferenze
4. Non inventare piatti non nel menu
5. Se qualcosa non è disponibile, proponi alternative
6. Proponi abbinamenti (vino, contorni, dolci)
7. Per domande sui piatti, spiega ingredienti e preparazione
8. Se il cliente ha restrizioni alimentari, filtra i suggerimenti

FORMATO:
- Risposte conversazionali, calde e accoglienti
- Usa **grassetto** per i nomi dei piatti
- Quando confermi un ordine, elenca cosa è stato aggiunto"""

    def _analyze_message(self, message: str) -> MessageAnalysis:
        """Analizza il messaggio usando GPT"""
        prompt = f"""Analizza questo messaggio di un cliente al ristorante.

Messaggio: "{message}"

Contesto ordine attuale: {self.order.get_summary() if not self.order.is_empty() else "vuoto"}

Rispondi in JSON con:
{{
    "is_order": true/false (sta ordinando qualcosa?),
    "is_question": true/false (sta facendo una domanda?),
    "is_modification": true/false (vuole modificare l'ordine?),
    "items": [lista di nomi piatti che sta ordinando, vuota se non ordina],
    "preferences": {{
        "vegetariano": true/false/null,
        "vegano": true/false/null,
        "allergeni": [lista stringhe es. "glutine", "lattosio"] o [],
        "diabetico": true/false/null
    }},
    "needs_clarification": true/false (il messaggio è ambiguo?),
    "clarification_reason": "motivo se needs_clarification"
}}

IMPORTANTE:
- "items" deve contenere SOLO nomi di piatti specifici che il cliente vuole ordinare
- Se dice qualcosa di generico come "un vino rosso", items = [] (non è un piatto specifico)
- Se dice "quello" o "lo prendo", cerca di capire a cosa si riferisce dal contesto
- Se esprime preferenze alimentari, riportale in "preferences"
"""

        try:
            result = self.llm.generate_json(
                [{"role": "user", "content": prompt}],
                max_tokens=500
            )

            # Parsing items: cerca match nel menu
            extracted_items = []
            for item_name in result.get("items", []):
                menu_item = self.menu.find_by_name(item_name)
                if menu_item:
                    extracted_items.append(menu_item.to_dict())

            return MessageAnalysis(
                is_order=result.get("is_order", False),
                is_question=result.get("is_question", False),
                is_modification=result.get("is_modification", False),
                extracted_items=extracted_items,
                preferences_detected=result.get("preferences", {}),
                needs_clarification=result.get("needs_clarification", False),
                clarification_reason=result.get("clarification_reason", "")
            )

        except Exception as e:
            print(f"[WAITER] Error analyzing message: {e}")
            return MessageAnalysis(
                is_order=False,
                is_question=True,
                is_modification=False,
                extracted_items=[],
                preferences_detected={},
                needs_clarification=False
            )

    def _update_preferences(self, preferences: Dict):
        """Aggiorna le preferenze del cliente"""
        if preferences.get("vegetariano"):
            self.order.set_preference("vegetariano", True)
        if preferences.get("vegano"):
            self.order.set_preference("vegano", True)
        if preferences.get("diabetico"):
            self.order.set_preference("note", "diabetico - evitare zuccheri")

        allergeni = preferences.get("allergeni", [])
        for allergen in allergeni:
            self.order.set_preference("intolleranze", allergen)

    def _add_items_to_order(self, items: List[Dict]) -> List[str]:
        """Aggiunge items all'ordine, ritorna lista di nomi aggiunti"""
        added = []
        for item in items:
            # Verifica se già presente
            existing = any(
                oi.id == item.get("id", item["nome"])
                for oi in self.order.items
            )
            if not existing:
                self.order.add_from_menu_item(item)
                added.append(item["nome"])
        return added

    def chat(self, user_message: str) -> str:
        """
        Elabora il messaggio dell'utente e genera risposta.
        """
        # 1. Analizza il messaggio
        analysis = self._analyze_message(user_message)

        # 2. Aggiorna preferenze se rilevate
        if analysis.preferences_detected:
            self._update_preferences(analysis.preferences_detected)

        # 3. Aggiungi items all'ordine se è un ordine
        added_items = []
        if analysis.is_order and analysis.extracted_items:
            added_items = self._add_items_to_order(analysis.extracted_items)
            if added_items:
                print(f"[WAITER] Aggiunti all'ordine: {added_items}")

        # 4. Costruisci contesto per la risposta
        context_note = ""
        if added_items:
            context_note = f"\n\n[SISTEMA: Hai appena aggiunto all'ordine: {', '.join(added_items)}. Conferma al cliente.]"
        elif analysis.is_order and not analysis.extracted_items:
            context_note = "\n\n[SISTEMA: Il cliente sembra voler ordinare ma non hai trovato piatti specifici. Chiedi chiarimenti o suggerisci opzioni.]"

        # 5. Genera risposta
        messages = [
            {"role": "system", "content": self._get_system_prompt() + context_note}
        ]

        # Aggiungi cronologia (ultimi 10 messaggi)
        messages.extend(self.conversation_history[-10:])
        messages.append({"role": "user", "content": user_message})

        try:
            response = self.llm.generate(messages, temperature=0.8)
        except Exception as e:
            response = f"Mi scuso, ho avuto un problema. Può ripetere? (Errore: {e})"

        # 6. Aggiorna cronologia
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": response})

        return response

    def get_greeting(self) -> str:
        """Genera messaggio di benvenuto"""
        return self.chat("Salve, sono appena arrivato al ristorante.")

    def get_order_summary(self) -> str:
        """Ritorna riepilogo ordine"""
        return self.order.get_summary()

    def clear_order(self):
        """Svuota l'ordine"""
        self.order.clear()

    def confirm_order(self) -> str:
        """Conferma l'ordine"""
        if self.order.is_empty():
            return "Non hai ancora ordinato nulla!"

        self.order.confirm()
        return f"Ordine confermato!\n\n{self.order.get_summary()}\n\nGrazie per aver ordinato!"

    def get_conversation_history(self) -> List[Dict]:
        """Ritorna cronologia conversazione"""
        return self.conversation_history

    def reset(self):
        """Reset completo"""
        self.order.clear()
        self.conversation_history = []
        self.phase = ConversationPhase.GREETING
