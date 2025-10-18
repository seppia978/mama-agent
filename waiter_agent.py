"""
Waiter Agent - Intelligent conversational agent for restaurant ordering
"""
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from llm_provider import LLMProvider


class ConversationPhase(Enum):
    """Phases of the conversation"""
    GREETING = "greeting"
    TAKING_ORDER = "taking_order"
    SUGGESTIONS = "suggestions"
    CONFIRMING = "confirming"
    COMPLETED = "completed"


@dataclass
class Order:
    """Represents a customer order"""
    items: List[Dict[str, Any]] = field(default_factory=list)
    total: float = 0.0
    special_requests: List[str] = field(default_factory=list)

    def add_item(self, item: Dict[str, Any], quantity: int = 1):
        """Add item to order"""
        self.items.append({
            "item": item,
            "quantity": quantity
        })
        self.total += item["prezzo"] * quantity

    def remove_item(self, item_id: str) -> bool:
        """Remove item from order"""
        for i, order_item in enumerate(self.items):
            if order_item["item"]["id"] == item_id:
                self.total -= order_item["item"]["prezzo"] * order_item["quantity"]
                self.items.pop(i)
                return True
        return False

    def get_summary(self) -> str:
        """Get order summary"""
        if not self.items:
            return "Nessun ordine ancora."

        summary = "Il tuo ordine:\n"
        for order_item in self.items:
            item = order_item["item"]
            qty = order_item["quantity"]
            summary += f"- {item['nome']} x{qty} ({item['prezzo'] * qty:.2f}€)\n"

        summary += f"\nTotale: {self.total:.2f}€"

        if self.special_requests:
            summary += f"\nRichieste speciali: {', '.join(self.special_requests)}"

        return summary


class WaiterAgent:
    """
    Intelligent waiter agent that helps customers order from a menu
    """

    def __init__(self, menu: Dict[str, Any], llm_provider: LLMProvider):
        self.menu = menu
        self.llm = llm_provider
        self.order = Order()
        self.conversation_history: List[Dict[str, str]] = []
        self.phase = ConversationPhase.GREETING
        self.customer_preferences = {
            "vegetarian": None,
            "allergies": [],
            "budget": None,
            "spicy_preference": None
        }

        # Initialize system prompt
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the LLM"""
        menu_text = self._format_menu_for_llm()

        return f"""Sei un cameriere esperto e cordiale del ristorante "{self.menu['ristorante']}".
Il tuo obiettivo è aiutare il cliente a fare un'ordinazione piacevole e soddisfacente.

PERSONALITÀ:
- Sei amichevole, professionale e attento
- Conosci perfettamente il menu e puoi dare suggerimenti personalizzati
- Fai domande per capire le preferenze del cliente
- Suggerisci piatti in modo naturale, senza essere invadente
- Sei proattivo nel proporre abbinamenti (es. vino con i piatti)
- Informi sui tempi di preparazione se rilevante
- Gestisci allergie e preferenze alimentari con cura

MENU DEL RISTORANTE:
{menu_text}

REGOLE IMPORTANTI:
1. Rispondi SEMPRE in italiano in modo naturale e cordiale
2. Quando il cliente ordina qualcosa, conferma l'ordine
3. Suggerisci piatti basandoti sulle preferenze espresse
4. Se il cliente chiede consigli, proponi 2-3 opzioni con spiegazioni
5. Ricorda allergie e preferenze durante tutta la conversazione
6. Proponi abbinamenti (antipasto+primo, vino+cibo, dolce+digestivo)
7. Non inventare piatti che non sono nel menu
8. Se il cliente chiede qualcosa non disponibile, proponi alternative simili

FORMATO RISPOSTE:
- Rispondi in modo conversazionale come un vero cameriere
- Usa un tono caldo e accogliente
- Fai domande aperte per capire meglio cosa desidera il cliente
- Quando possibile, aggiungi dettagli appetitosi sui piatti

Inizia salutando il cliente e chiedendo cosa desidera ordinare."""

    def _format_menu_for_llm(self) -> str:
        """Format menu in a readable way for the LLM"""
        menu_text = ""
        for categoria, items in self.menu["categorie"].items():
            menu_text += f"\n{categoria.upper()}:\n"
            for item in items:
                menu_text += f"- {item['nome']} ({item['prezzo']}€): {item['descrizione']}"
                if "suggerimenti" in item:
                    menu_text += f" | Suggerimento: {item['suggerimenti']}"
                if item.get("vegetariano"):
                    menu_text += " [VEGETARIANO]"
                if item.get("vegano"):
                    menu_text += " [VEGANO]"
                if "allergeni" in item and item["allergeni"]:
                    menu_text += f" | Allergeni: {', '.join(item['allergeni'])}"
                menu_text += "\n"
        return menu_text

    def _build_context_message(self) -> str:
        """Build context message about current order and preferences"""
        context = ""

        # Add current order
        if self.order.items:
            context += f"\nORDINE CORRENTE:\n{self.order.get_summary()}\n"

        # Add customer preferences
        prefs = []
        if self.customer_preferences["vegetarian"]:
            prefs.append("vegetariano")
        if self.customer_preferences["allergies"]:
            prefs.append(f"allergie: {', '.join(self.customer_preferences['allergies'])}")
        if self.customer_preferences["spicy_preference"]:
            prefs.append(f"piccante: {self.customer_preferences['spicy_preference']}")

        if prefs:
            context += f"\nPREFERENZE CLIENTE: {' | '.join(prefs)}\n"

        return context

    def chat(self, user_message: str) -> str:
        """
        Process user message and generate response

        Args:
            user_message: Message from the customer

        Returns:
            Agent's response
        """
        # Detect and update customer preferences
        self._extract_preferences(user_message)

        # Detect if customer is ordering items
        self._detect_order_items(user_message)

        # Build messages for LLM
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add context about current state
        context = self._build_context_message()
        if context:
            messages.append({"role": "system", "content": context})

        # Add conversation history (last 10 messages to avoid context overflow)
        messages.extend(self.conversation_history[-10:])

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        # Generate response
        try:
            response = self.llm.generate(messages, temperature=0.8)
        except Exception as e:
            response = f"Mi scuso, ho avuto un problema tecnico. Può ripetere per favore? (Errore: {e})"

        # Update conversation history
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": response})

        return response

    def _extract_preferences(self, message: str):
        """Extract customer preferences from message"""
        message_lower = message.lower()

        # Vegetarian/vegan
        if "vegetariano" in message_lower or "vegetariana" in message_lower:
            self.customer_preferences["vegetarian"] = True
        if "vegano" in message_lower or "vegana" in message_lower:
            self.customer_preferences["vegetarian"] = True

        # Allergies
        common_allergens = ["glutine", "lattosio", "uova", "solfiti", "frutta secca"]
        for allergen in common_allergens:
            if allergen in message_lower and "allergi" in message_lower:
                if allergen not in self.customer_preferences["allergies"]:
                    self.customer_preferences["allergies"].append(allergen)

        # Spicy preference
        if "piccante" in message_lower:
            if "non" in message_lower or "senza" in message_lower:
                self.customer_preferences["spicy_preference"] = "no"
            else:
                self.customer_preferences["spicy_preference"] = "yes"

    def _detect_order_items(self, message: str):
        """Detect if customer is ordering specific items and add them to order"""
        message_lower = message.lower()

        # Simple keyword matching for orders
        # In a production system, you might want to use the LLM to extract structured data
        for categoria, items in self.menu["categorie"].items():
            for item in items:
                item_name_lower = item["nome"].lower()
                # Check if item name is mentioned
                if item_name_lower in message_lower:
                    # Check for ordering keywords
                    if any(keyword in message_lower for keyword in ["prendo", "vorrei", "voglio", "ordino", "porto"]):
                        # Check if not already in order
                        if not any(order_item["item"]["id"] == item["id"] for order_item in self.order.items):
                            self.order.add_item(item)

    def get_order(self) -> Order:
        """Get current order"""
        return self.order

    def reset_order(self):
        """Reset the current order"""
        self.order = Order()

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get conversation history"""
        return self.conversation_history

    def search_menu(self, query: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Search menu items based on query and filters

        Args:
            query: Search query
            filters: Optional filters (vegetarian, max_price, category, etc.)

        Returns:
            List of matching items
        """
        results = []
        query_lower = query.lower() if query else ""

        for categoria, items in self.menu["categorie"].items():
            for item in items:
                # Apply filters
                if filters:
                    if filters.get("vegetarian") and not item.get("vegetariano"):
                        continue
                    if filters.get("max_price") and item["prezzo"] > filters["max_price"]:
                        continue
                    if filters.get("category") and categoria != filters["category"]:
                        continue
                    if filters.get("exclude_allergens"):
                        if any(allergen in item.get("allergeni", []) for allergen in filters["exclude_allergens"]):
                            continue

                # Search in name and description
                if query_lower:
                    if (query_lower in item["nome"].lower() or
                        query_lower in item.get("descrizione", "").lower()):
                        results.append({**item, "categoria": categoria})
                else:
                    results.append({**item, "categoria": categoria})

        return results
