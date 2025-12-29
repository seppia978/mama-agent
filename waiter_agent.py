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
9. Se il cliente chiede informazioni su un piatto del menu (significato del nome, ingredienti, preparazione), rispondi in modo professionale spiegando il piatto
10. Se il cliente fa domande sui prezzi o sul menu, rispondi senza aggiungere nulla all'ordine

FORMATO RISPOSTE:
- Rispondi in modo conversazionale come un vero cameriere
- Usa un tono caldo e accogliente
- Fai domande aperte per capire meglio cosa desidera il cliente
- Quando possibile, aggiungi dettagli appetitosi sui piatti

Inizia salutando il cliente e chiedendo cosa desidera ordinare.

IMPORTANTE: NON DIVAGARE MAI SU ARGOMENTI NON RELATIVI AL RISTORANTE O ALL'ORDINE, O A DETTAGLI SU PIATTI E CUCINA."""

    def _format_menu_for_llm(self) -> str:
        """Format menu in a readable way for the LLM"""
        menu_text = f"\nMENU - {self.menu.get('ristorante', 'Ristorante')}\n"
        if 'edizione' in self.menu:
            menu_text += f"Edizione: {self.menu['edizione']}\n"
        
        # Support both old format (categorie) and new format (sezioni)
        sections = self.menu.get("sezioni", [])
        if sections:
            # New format with sezioni
            for sezione in sections:
                menu_text += f"\n{sezione['nome'].upper()}:\n"
                for item in sezione.get('voci', []):
                    # Handle items with sizes/taglie
                    if 'taglie' in item:
                        menu_text += f"- {item['nome']}:\n"
                        for taglia in item['taglie']:
                            menu_text += f"  * {taglia['nome']}: €{taglia.get('prezzo', 0):.2f}\n"
                    else:
                        prezzo = item.get('prezzo')
                        if prezzo is not None:
                            menu_text += f"- {item['nome']} (€{prezzo:.2f})"
                        else:
                            menu_text += f"- {item['nome']}"
                        if "descrizione" in item:
                            menu_text += f": {item['descrizione']}"
                        if "varianti" in item:
                            menu_text += f" | Varianti: {', '.join(item['varianti'][:3])}..."
                        menu_text += "\n"
                    
                    # Add allergen info
                    if "allergeni" in item and item["allergeni"]:
                        allergeni_legend = self.menu.get('allergeni_legend', {})
                        allergeni_nomi = [allergeni_legend.get(str(a), str(a)) for a in item['allergeni']]
                        menu_text += f"  Allergeni: {', '.join(allergeni_nomi)}\n"
        else:
            # Old format with categorie
            for categoria, items in self.menu.get("categorie", {}).items():
                menu_text += f"\n{categoria.upper()}:\n"
                for item in items:
                    menu_text += f"- {item['nome']} (€{item.get('prezzo', 0):.2f}): {item.get('descrizione', '')}"
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

    def _extract_order_with_llm(self, user_message: str, assistant_response: str) -> List[Dict]:
        """
        Extract ordered items using keyword matching + fuzzy search
        More reliable than pure LLM extraction with small models
        """
        # Simple but effective: check for ordering keywords
        message_lower = user_message.lower()
        
        # Check if this is an order confirmation
        order_keywords = ["prendo", "vorrei", "voglio", "ordino", "porto", "portare", "prendiamo", "per me"]
        question_keywords = ["costa", "prezzo", "cos'è", "cos è", "cosa è", "cosa significa", "che significa", "come", "che tipo", "quale", "mi consigli", "suggerisci", "cosa", "quanto", "che cos'è"]
        
        # Strong indicators that it's NOT an order (information requests)
        non_order_phrases = [
            "nel menu c'è",
            "vedo che",
            "ho visto",
            "c'è una voce",
            "che significa",
            "cosa significa",
            "cos'è",
            "che cos'è",
            "mi spieghi",
            "puoi spiegarmi",
            "vorrei sapere",
            "mi dici",
            "mi puoi dire",
            "chiamata",
            "chiamato"
        ]
        
        # Check for non-order phrases (strong indicators of questions)
        is_info_request = any(phrase in message_lower for phrase in non_order_phrases)
        
        # If it's clearly an information request, don't extract
        if is_info_request:
            print(f"🚫 Rilevata domanda informativa, skip estrazione ordine")
            print(f"   Frase rilevata: {[p for p in non_order_phrases if p in message_lower]}")
            return []
        
        # Conferme implicite/cumulative: aggiungi suggerimenti dell'assistente
        # PRIMA di controllare le keyword di ordine esplicito
        conferma_keywords = [
            "facciamo", "aggiungi", "aggiungili", "aggiungile", "aggiungilo", "aggiungiamoli", 
            "ok", "va bene", "perfetto", "conferma", "prendiamo anche", "prendiamo sia", 
            "prendiamo tutti", "prendiamo tutto", "va bene sia", "va bene entrambi", 
            "va bene tutti", "prendiamo questi", "prendiamo quelle", "aggiungilo all'ordine",
            "aggiungili all'ordine", "mettilo nell'ordine", "mettili nell'ordine"
        ]
        if any(kw in message_lower for kw in conferma_keywords):
            # Estrai tutti i piatti/vini suggeriti nell'ultima risposta dell'assistente
            if assistant_response:
                response_lower = assistant_response.lower()
                found_items = []
                # Get already ordered items to avoid duplicates
                already_ordered = {order_item["item"]["nome"].lower() for order_item in self.order.items}
                
                # Cerca tutti i piatti del menu menzionati nella risposta
                for sezione in self.menu.get("sezioni", []):
                    for item in sezione.get('voci', []):
                        item_name = item["nome"].lower()
                        # Skip if already in order or already in found_items
                        if item_name in already_ordered:
                            continue
                        if any(f["nome"].lower() == item_name for f in found_items):
                            continue
                        # Check if mentioned in response (exact match)
                        if item_name in response_lower:
                            found_items.append({"nome": item["nome"], "taglia": None})
                            continue
                        
                        # Fuzzy matching per vini (es. "Vermentino" → "Vermentino di Gallura")
                        item_words = set(item_name.split())
                        response_words = set(response_lower.split())
                        # Se almeno una parola del nome del piatto (escluse parole comuni) è nella risposta
                        common_words = {'di', 'del', 'della', 'il', 'la', 'e', 'con', 'alla', 'al'}
                        meaningful_words = item_words - common_words
                        if meaningful_words and any(word in response_words for word in meaningful_words):
                            # Verifica che sia plausibile (es. "vino vermentino" → trova "Vermentino di Gallura")
                            if any(word in response_lower for word in meaningful_words):
                                found_items.append({"nome": item["nome"], "taglia": None})
                
                # Cerca anche nelle categorie vecchie
                for categoria, items in self.menu.get("categorie", {}).items():
                    for item in items:
                        item_name = item["nome"].lower()
                        # Skip if already in order or already in found_items
                        if item_name in already_ordered:
                            continue
                        if any(f["nome"].lower() == item_name for f in found_items):
                            continue
                        # Check if mentioned in response (exact match)
                        if item_name in response_lower:
                            found_items.append({"nome": item["nome"], "taglia": None})
                            continue
                        
                        # Fuzzy matching
                        item_words = set(item_name.split())
                        response_words = set(response_lower.split())
                        common_words = {'di', 'del', 'della', 'il', 'la', 'e', 'con', 'alla', 'al'}
                        meaningful_words = item_words - common_words
                        if meaningful_words and any(word in response_words for word in meaningful_words):
                            if any(word in response_lower for word in meaningful_words):
                                found_items.append({"nome": item["nome"], "taglia": None})
                
                if found_items:
                    print(f"✨ Conferma implicita: aggiungo suggeriti: {[f['nome'] for f in found_items]}")
                    return found_items
                
                # SOLO se non ha trovato nulla nel menu, cerca voci personalizzate (vini generici, bevande)
                # Pattern per vini generici: "vino [nome]", "calice di [nome]"
                print("⚠️ Nessun item trovato nel menu, cerco voci personalizzate...")
                import re
                custom_items = []
                wine_patterns = [
                    r'vino\s+(\w+)',
                    r'calice\s+di\s+(\w+)',
                    r'bottiglia\s+di\s+(\w+)',
                ]
                for pattern in wine_patterns:
                    matches = re.findall(pattern, response_lower, re.IGNORECASE)
                    for wine_name in matches:
                        wine_name = wine_name.strip().capitalize()
                        if wine_name and wine_name.lower() not in already_ordered:
                            # Verifica che non sia già nel menu (controllo doppio)
                            found_in_menu = False
                            for sezione in self.menu.get("sezioni", []):
                                for item in sezione.get('voci', []):
                                    if wine_name.lower() in item["nome"].lower():
                                        found_in_menu = True
                                        break
                                if found_in_menu:
                                    break
                            
                            if not found_in_menu:
                                # Crea voce personalizzata per il vino
                                custom_item = {
                                    "nome": f"Vino {wine_name}",
                                    "taglia": None,
                                    "prezzo": 0.0,  # Prezzo da definire
                                    "custom": True
                                }
                                custom_items.append(custom_item)
                                print(f"🍷 Creata voce personalizzata: {custom_item['nome']} (prezzo da verificare)")
                
                if custom_items:
                    return custom_items
        
        # Skip if it's clearly ONLY a question (no order intent)
        has_question = any(q in message_lower for q in question_keywords)
        has_order = any(o in message_lower for o in order_keywords)
        
        # If it has question words but no order keywords, skip
        if has_question and not has_order:
            return []
        
        # Only extract if there are explicit ordering keywords
        if not has_order:
            return []

        # Riconoscimento acqua anche se non è nel menu
        acqua_keywords = ["acqua", "bottiglia d'acqua", "bicchiere d'acqua", "acqua naturale", "acqua frizzante"]
        if any(kw in message_lower for kw in acqua_keywords):
            print("💧 Aggiungo acqua all'ordine (voce gratuita)")
            return [{"nome": "Acqua", "taglia": None, "prezzo": 0.0}]

        # Check for pronoun references (lo/la prendo, questo, quello)
        # In this case, look at the assistant's last response for context
        pronoun_phrases = ["lo prendo", "la prendo", "li prendo", "le prendo", "lo voglio", "la voglio", 
                          "questo", "quella", "quello", "questi", "quelli", "perfetto! lo", "ok! lo", "va bene! lo"]
        uses_pronoun = any(phrase in message_lower for phrase in pronoun_phrases)
        
        if uses_pronoun and assistant_response:
            # Extract item names from assistant's response (the item being discussed)
            response_lower = assistant_response.lower()
            for sezione in self.menu.get("sezioni", []):
                for item in sezione.get('voci', []):
                    item_name_lower = item["nome"].lower()
                    # Check if the assistant was talking about this item
                    if item_name_lower in response_lower:
                        taglia = None
                        if 'taglie' in item:
                            if 'grande' in message_lower or 'grosso' in message_lower:
                                taglia = 'grande'
                            elif 'piccolo' in message_lower:
                                taglia = 'piccolo'
                            else:
                                taglia = 'piccolo'  # Default
                        print(f"✨ Riferimento pronominale rilevato: '{item['nome']}' (dal contesto)")
                        return [{"nome": item["nome"], "taglia": taglia}]
            
            # Check old format too
            for categoria, items in self.menu.get("categorie", {}).items():
                for item in items:
                    if item["nome"].lower() in response_lower:
                        print(f"✨ Riferimento pronominale rilevato: '{item['nome']}' (dal contesto)")
                        return [{"nome": item["nome"], "taglia": None}]
        
        # Extract items by searching menu
        found_items = []
        
        # Support both old and new format
        sections = self.menu.get("sezioni", [])
        if sections:
            # New format
            for sezione in sections:
                for item in sezione.get('voci', []):
                    item_name = item["nome"].lower()
                    
                    # Check if item name appears in message
                    # Use partial matching for better results
                    words_in_message = set(message_lower.split())
                    words_in_item = set(item_name.split())
                    
                    # Check for direct mention or key words match
                    if (item_name in message_lower or 
                        len(words_in_item & words_in_message) >= min(2, len(words_in_item))):
                        
                        # Determine size if applicable
                        taglia = None
                        if 'taglie' in item:
                            if 'grande' in message_lower or 'grosso' in message_lower:
                                taglia = 'grande'
                            elif 'piccolo' in message_lower:
                                taglia = 'piccolo'
                            else:
                                taglia = 'piccolo'  # Default
                        
                        found_items.append({"nome": item["nome"], "taglia": taglia})
                        break  # Only match once per section
        else:
            # Old format
            for categoria, items in self.menu.get("categorie", {}).items():
                for item in items:
                    item_name = item["nome"].lower()
                    if item_name in message_lower:
                        found_items.append({"nome": item["nome"], "taglia": None})
                        break
        
        return found_items

    def _find_menu_item(self, item_name: str, taglia: str = None, custom_price: float = None) -> Optional[Dict]:
        """Find menu item by name and optional size, or create custom item"""
        item_name_lower = item_name.lower()
        
        # Check if it's a custom item (e.g., wine not in menu)
        if custom_price is not None:
            return {
                'nome': item_name,
                'prezzo': custom_price,
                'id': item_name,
                'custom': True
            }
        
        # Search in new format (sezioni)
        sections = self.menu.get("sezioni", [])
        if sections:
            for sezione in sections:
                for item in sezione.get('voci', []):
                    if item_name_lower in item["nome"].lower() or item["nome"].lower() in item_name_lower:
                        # Handle items with sizes
                        if 'taglie' in item and taglia:
                            for t in item['taglie']:
                                if taglia.lower() in t['nome'].lower():
                                    return {
                                        **item,
                                        'nome': f"{item['nome']} ({t['nome']})",
                                        'prezzo': t['prezzo'],
                                        'id': f"{item['nome']}_{t['nome']}"
                                    }
                            # If size not found, use first
                            t = item['taglie'][0]
                            return {
                                **item,
                                'nome': f"{item['nome']} ({t['nome']})",
                                'prezzo': t['prezzo'],
                                'id': f"{item['nome']}_{t['nome']}"
                            }
                        elif 'prezzo' in item:
                            if 'id' not in item:
                                item['id'] = item['nome']
                            return item
        
        # Search in old format (categorie)
        for categoria, items in self.menu.get("categorie", {}).items():
            for item in items:
                if item_name_lower in item["nome"].lower() or item["nome"].lower() in item_name_lower:
                    return item
        
        return None

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

        # Extract and add ordered items using LLM
        ordered_items = self._extract_order_with_llm(user_message, response)
        
        if ordered_items:
            print(f"🔍 Items estratti dall'LLM: {ordered_items}")
            for item_data in ordered_items:
                item_name = item_data.get('nome', '')
                taglia = item_data.get('taglia')
                custom_price = item_data.get('prezzo')
                
                # Find item in menu (or create custom item)
                menu_item = self._find_menu_item(item_name, taglia, custom_price)
                
                if menu_item:
                    # Check if not already in order
                    item_id = menu_item.get('id', menu_item['nome'])
                    if not any(order_item["item"].get("id") == item_id for order_item in self.order.items):
                        self.order.add_item(menu_item)
                        if menu_item.get('custom'):
                            print(f"✅ Aggiunto all'ordine: {menu_item['nome']} - €{menu_item.get('prezzo', 0):.2f} (prezzo da verificare)")
                        else:
                            print(f"✅ Aggiunto all'ordine: {menu_item['nome']} - €{menu_item.get('prezzo', 0):.2f}")

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
        
        # Support both old format (categorie) and new format (sezioni)
        sections = self.menu.get("sezioni", [])
        if sections:
            # New format with sezioni
            for sezione in sections:
                for item in sezione.get('voci', []):
                    item_name_lower = item["nome"].lower()
                    # Check if item name is mentioned
                    if item_name_lower in message_lower:
                        # Check for ordering keywords
                        if any(keyword in message_lower for keyword in ["prendo", "vorrei", "voglio", "ordino", "porto"]):
                            # For items with sizes, try to detect which size
                            if 'taglie' in item:
                                # Try to detect size
                                if 'grande' in message_lower:
                                    taglia = next((t for t in item['taglie'] if 'grande' in t['nome'].lower()), item['taglie'][0])
                                elif 'piccolo' in message_lower:
                                    taglia = next((t for t in item['taglie'] if 'piccolo' in t['nome'].lower()), item['taglie'][0])
                                else:
                                    taglia = item['taglie'][0]  # Default to first size
                                
                                # Create item with selected size
                                item_with_size = {
                                    **item,
                                    'nome': f"{item['nome']} ({taglia['nome']})",
                                    'prezzo': taglia['prezzo'],
                                    'id': f"{item['nome']}_{taglia['nome']}"
                                }
                                # Check if not already in order
                                if not any(order_item["item"].get("id") == item_with_size["id"] for order_item in self.order.items):
                                    self.order.add_item(item_with_size)
                            else:
                                # Regular item
                                if 'id' not in item:
                                    item['id'] = item['nome']  # Use name as ID if not present
                                # Check if not already in order
                                if not any(order_item["item"].get("id") == item.get("id") for order_item in self.order.items):
                                    self.order.add_item(item)
        else:
            # Old format with categorie
            for categoria, items in self.menu.get("categorie", {}).items():
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

        # Support both old format (categorie) and new format (sezioni)
        sections = self.menu.get("sezioni", [])
        if sections:
            # New format with sezioni
            for sezione in sections:
                categoria = sezione['nome']
                for item in sezione.get('voci', []):
                    # Apply filters
                    if filters:
                        item_prezzo = item.get('prezzo', 0)
                        if 'taglie' in item:
                            item_prezzo = min(t['prezzo'] for t in item['taglie'])
                        
                        if filters.get("vegetarian") and not item.get("vegetariano"):
                            continue
                        if filters.get("max_price") and item_prezzo > filters["max_price"]:
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
        else:
            # Old format with categorie
            for categoria, items in self.menu.get("categorie", {}).items():
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
