"""
Supervisor Agent - Monitors user messages for order intent and menu compliance
"""
from typing import Dict, Any, List, Optional, Tuple
import re
from difflib import SequenceMatcher
from llm_provider import LLMProvider


class SupervisorAgent:
    """
    Agent that monitors user messages to:
    1. Estimate order intent probability (> tau means it's an order)
    2. Verify if mentioned items exist in menu with high probability
    If conditions fail, prompts waiter to seek clarification
    """

    def __init__(self, llm_provider: LLMProvider, menu: Dict[str, Any], tau: float = 0.7):
        self.llm_provider = llm_provider
        self.menu = menu
        self.tau = tau  # Threshold for order intent

    def analyze_message(self, user_message: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Analyze user message for order intent and menu compliance.
        Returns dict with analysis results and any clarification needed.
        """
        # Step 1: Estimate order intent probability
        order_prob = self._estimate_order_probability(user_message)

        result = {
            "is_order": order_prob > self.tau,
            "order_probability": order_prob,
            "needs_clarification": False,
            "clarification_type": None,
            "clarification_message": None,
            "extracted_items": [],
            "menu_compliance": True,
            "suggested_items": []
        }

        # Step 2: If it's likely an order, extract and verify items
        if result["is_order"]:
            extracted_items = self._extract_order_items(user_message, conversation_history)
            result["extracted_items"] = extracted_items

            # Check if items exist in menu or conversation history
            compliance_result = self._check_menu_compliance(extracted_items, conversation_history)
            result.update(compliance_result)

            # If items don't comply, find suggestions
            if not result["menu_compliance"]:
                result["suggested_items"] = self._find_similar_items(extracted_items, conversation_history)
                result["needs_clarification"] = True
                result["clarification_type"] = "item_confirmation"
                result["clarification_message"] = self._build_item_confirmation_message(
                    extracted_items, result["suggested_items"]
                )
        else:
            # Not confident it's an order - do NOT ask for clarification, let waiter respond normally
            result["needs_clarification"] = False
            result["clarification_type"] = None
            result["clarification_message"] = None

        return result

    def _estimate_order_probability(self, message: str) -> float:
        """
        Estimate order probability using rule-based approach with LLM fallback.
        """
        message_lower = message.lower()

        # High probability indicators
        high_prob_words = ['prendo', 'vorrei', 'ordino', 'portami', 'dammi', 'voglio', 'consigliami', 'raccomanda', 'cosa prendi']
        medium_prob_words = ['pizza', 'pasta', 'spaghetti', 'vino', 'birra', 'caffè', 'dolce', 'menu', 'ordinare', 'cena', 'pranzo']
        question_words = ['che', 'quale', 'cosa']

        # Count indicators
        high_count = sum(1 for word in high_prob_words if word in message_lower)
        medium_count = sum(1 for word in medium_prob_words if word in message_lower)
        question_count = sum(1 for word in question_words if word in message_lower)

        # Rule-based probability
        if high_count > 0:
            base_prob = 0.9
        elif medium_count > 1:
            base_prob = 0.7
        elif question_count > 0 and medium_count > 0:
            base_prob = 0.4  # Questions about food are not orders
        elif medium_count > 0:
            base_prob = 0.6
        else:
            base_prob = 0.1

        # Special handling for recommendation requests
        if 'consigliami' in message_lower or 'raccomanda' in message_lower or 'cosa consigli' in message_lower:
            base_prob = 0.3  # Recommendations are not orders

        # Use LLM only for borderline cases (0.3-0.7)
        if 0.3 <= base_prob <= 0.7:
            try:
                prompt = f'Order probability for: "{message}"\nReturn only 0.0-1.0:'
                messages = [{"role": "user", "content": prompt}]
                response = self.llm_provider.generate(messages, max_tokens=5)
                match = re.search(r'(\d+\.?\d*)', response.strip())
                if match:
                    llm_prob = float(match.group(1))
                    # Blend rule-based and LLM
                    return (base_prob * 0.7) + (llm_prob * 0.3)
            except:
                pass

        return base_prob

    def _extract_order_items(self, message: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> List[str]:
        """
        Extract order items dynamically from menu and conversation history.
        """
        items = []
        message_lower = message.lower()

        # Step 1: Build dynamic patterns from actual menu items
        menu_items = self._get_all_menu_items()

        for menu_item in menu_items:
            item_name = menu_item["nome"].lower()

            # Check for exact match
            if item_name in message_lower:
                if item_name not in items:
                    items.append(item_name)
                continue

            # Check for partial match (key words from item name)
            item_words = [w for w in item_name.split() if len(w) > 3]
            # Exclude common words
            common_words = {'alla', 'alle', 'dello', 'della', 'degli', 'delle', 'con', 'senza', 'piccolo', 'grande'}
            item_words = [w for w in item_words if w not in common_words]

            for word in item_words:
                if re.search(r'\b' + re.escape(word) + r'\b', message_lower):
                    # Found a key word - add the full menu item name
                    if item_name not in items:
                        items.append(item_name)
                    break

        # Step 2: Check conversation history for items mentioned by waiter
        if conversation_history and not items:
            # User might be referring to something the waiter suggested
            history_items = self._extract_items_from_conversation_context(message_lower, conversation_history)
            for item in history_items:
                if item not in items:
                    items.append(item)

        # Step 3: Handle generic references (il, la, lo, quello, questa, etc.)
        generic_refs = ['lo', 'la', 'li', 'le', 'quello', 'quella', 'questo', 'questa', 'quelli', 'quelle']
        has_generic_ref = any(re.search(r'\b' + ref + r'\b', message_lower) for ref in generic_refs)

        if has_generic_ref and not items and conversation_history:
            # Look for last mentioned item in waiter's response
            last_mentioned = self._get_last_mentioned_item_from_history(conversation_history)
            if last_mentioned and last_mentioned not in items:
                items.append(last_mentioned)

        return items

    def _get_all_menu_items(self) -> List[Dict[str, Any]]:
        """
        Get all items from the menu as a flat list.
        """
        all_items = []
        sections = self.menu.get("sezioni", [])

        for section in sections:
            for voce in section.get("voci", []):
                item = voce.copy()
                item["sezione"] = section["nome"]
                all_items.append(item)

        return all_items

    def _find_menu_item_by_name(self, item_name: str) -> Optional[Dict[str, Any]]:
        """
        Find a menu item by name (best match based on score).
        Returns the full menu item dict with id and prezzo.
        """
        item_name_lower = item_name.lower()
        best_match = None
        best_score = 0

        # Exclude common words from matching
        common_words = {'il', 'la', 'lo', 'i', 'gli', 'le', 'un', 'una', 'di', 'del', 'della',
                        'dello', 'dei', 'degli', 'delle', 'con', 'senza', 'alla', 'alle', 'al',
                        'piccolo', 'grande', 'per', 'due', 'persone'}

        sections = self.menu.get("sezioni", [])
        for section in sections:
            for voce in section.get("voci", []):
                menu_item_name = voce.get("nome", "").lower()
                score = 0

                # Exact match - highest priority
                if menu_item_name == item_name_lower:
                    result = voce.copy()
                    result["sezione"] = section["nome"]
                    if "id" not in result:
                        result["id"] = result["nome"]
                    return result  # Perfect match, return immediately

                # Partial match (item_name is contained in menu item or vice versa)
                if item_name_lower in menu_item_name:
                    score = 100 + len(item_name_lower)  # Longer match = better
                elif menu_item_name in item_name_lower:
                    score = 90 + len(menu_item_name)

                # Key word match - count how many significant words match
                if score == 0:
                    item_words = [w for w in item_name_lower.split() if w not in common_words and len(w) > 2]
                    menu_words = [w for w in menu_item_name.split() if w not in common_words and len(w) > 2]

                    matching_words = sum(1 for w in item_words if any(w in mw or mw in w for mw in menu_words))
                    if matching_words > 0:
                        # Score based on percentage of words matched
                        score = (matching_words / max(len(item_words), 1)) * 50

                if score > best_score:
                    best_score = score
                    best_match = voce.copy()
                    best_match["sezione"] = section["nome"]
                    if "id" not in best_match:
                        best_match["id"] = best_match["nome"]

        return best_match

    def _extract_items_from_conversation_context(self, message_lower: str, conversation_history: List[Dict[str, str]]) -> List[str]:
        """
        Extract items that were mentioned in conversation and user is now ordering.
        """
        items = []

        # Get dishes mentioned by waiter in recent messages
        mentioned_dishes = self._extract_mentioned_dishes_from_history(conversation_history)

        # Check if user message references any of these
        for dish in mentioned_dishes:
            dish_lower = dish.lower()
            dish_words = [w for w in dish_lower.split() if len(w) > 3]

            # Check if any significant word from the dish is in the user message
            for word in dish_words:
                if re.search(r'\b' + re.escape(word) + r'\b', message_lower):
                    if dish_lower not in items:
                        items.append(dish_lower)
                    break

        return items

    def _get_last_mentioned_item_from_history(self, conversation_history: List[Dict[str, str]]) -> Optional[str]:
        """
        Get the last item mentioned by the waiter in conversation.
        Useful when user says "lo prendo", "quello", etc.
        """
        # Look through assistant messages in reverse order
        for message in reversed(conversation_history):
            if message.get("role") == "assistant":
                content = message.get("content", "").lower()

                # Find menu items mentioned in this message
                for section in self.menu.get("sezioni", []):
                    for item in section.get("voci", []):
                        dish_name = item.get("nome", "").lower()
                        if dish_name in content and len(dish_name) > 3:
                            return dish_name

        return None

    def _check_menu_compliance(self, extracted_items: List[str], conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Check if extracted items exist in menu with high probability.
        Also check conversation history for previously mentioned dishes.
        Returns dict with compliance status.
        """
        compliant = True
        non_compliant_items = []

        for item in extracted_items:
            # First check if item exists in menu
            if not self._item_in_menu(item):
                # If not in menu, check if it was mentioned in conversation history
                history_match = self._find_dish_in_conversation_history(item, conversation_history) if conversation_history else None
                if not history_match:
                    compliant = False
                    non_compliant_items.append(item)

        return {
            "menu_compliance": compliant,
            "non_compliant_items": non_compliant_items
        }

    def _item_in_menu(self, item_name: str) -> bool:
        """
        Check if item exists in menu (case-insensitive partial match).
        """
        item_lower = item_name.lower()

        # Check all menu sections
        sections = self.menu.get("sezioni", [])
        for section in sections:
            for voce in section.get("voci", []):
                menu_item = voce.get("nome", "").lower()
                # Allow partial matches and fuzzy matching
                if item_lower in menu_item or menu_item in item_lower:
                    return True
                # Check similarity ratio
                if SequenceMatcher(None, item_lower, menu_item).ratio() > 0.8:
                    return True

        return False

    def _find_similar_items(self, extracted_items: List[str], conversation_history: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        Find most similar items in menu for non-compliant items.
        First check conversation history for previously mentioned dishes.
        """
        suggestions = []

        for item in extracted_items:
            if not self._item_in_menu(item):
                # First check conversation history
                history_match = self._find_dish_in_conversation_history(item, conversation_history) if conversation_history else None
                if history_match:
                    suggestions.append(history_match)
                else:
                    # Fall back to menu similarity search
                    similar = self._find_most_similar_item(item)
                    if similar:
                        suggestions.append({
                            "requested": item,
                            "suggested": similar["nome"],
                            "prezzo": similar["prezzo"],
                            "sezione": similar.get("sezione", "Menu")
                        })

        return suggestions

    def _find_most_similar_item(self, item_name: str) -> Optional[Dict[str, Any]]:
        """
        Find the most similar item in menu using category-aware fuzzy matching.
        """
        item_lower = item_name.lower()
        best_match = None
        best_ratio = 0.0

        # Determine likely category based on keywords
        category_keywords = {
            'pasta': ['pasta', 'spaghetti', 'penne', 'fusilli', 'risotto', 'lasagna', 'tagliatelle', 'carbonara', 'pomodoro', 'pesto'],
            'pizza': ['pizza', 'margherita', 'diavola', 'marina', 'quattro', 'formaggi', 'napoli', 'capricciosa'],
            'antipasti': ['antipasto', 'insalata', 'bruschetta', 'polenta', 'crudo', 'carpaccio', 'tartare'],
            'secondi': ['carne', 'pesce', 'pollo', 'maiale', 'tonno', 'salmone', 'branzino', 'baccala'],
            'contorni': ['patate', 'verdure', 'broccoli', 'insalata'],
            'bevande': ['vino', 'birra', 'acqua', 'caffè', 'bibita', 'spritz', 'aperitivo', 'digestivo'],
            'dolci': ['dolce', 'tiramisu', 'gelato', 'torta', 'cannolo', 'panna', 'cioccolato', 'croissant']
        }

        # Find which category the item belongs to
        item_category = None
        for category, keywords in category_keywords.items():
            if any(keyword in item_lower for keyword in keywords):
                item_category = category
                break

        sections = self.menu.get("sezioni", [])
        for section in sections:
            section_name = section["nome"].lower()
            
            # Skip sections that don't match the likely category
            if item_category:
                # Map menu sections to categories (using actual menu section names)
                section_to_category = {
                    'bistrot': 'pasta',  # Bistrot contains pasta dishes
                    'pizze': 'pizza',
                    'insalate': 'antipasti',  # Insalate section
                    'raw bar': 'antipasti',  # Raw fish
                    'caffetteria': 'bevande',
                    'colazione': 'dolci',  # Breakfast items
                    'estratti': 'bevande',
                    'tè': 'bevande'
                }
                
                section_category = None
                for sec, cat in section_to_category.items():
                    if sec in section_name:
                        section_category = cat
                        break
                
                # If we know the category but this section doesn't match, skip it
                if section_category and section_category != item_category:
                    continue

            for voce in section.get("voci", []):
                menu_item = voce.get("nome", "").lower()
                
                # Exact match gets highest score
                if item_lower == menu_item:
                    return voce.copy() | {"sezione": section["nome"]}
                
                # Check for shared keywords first
                requested_words = set(item_lower.split())
                menu_words = set(menu_item.split())
                common_words = requested_words & menu_words
                
                if common_words:
                    # If they share words, use similarity
                    ratio = SequenceMatcher(None, item_lower, menu_item).ratio()
                    # Boost for shared words
                    ratio *= (1 + len(common_words) * 0.2)
                else:
                    # No shared words, much lower similarity score
                    ratio = SequenceMatcher(None, item_lower, menu_item).ratio() * 0.3
                
                # Category boost
                if item_category and any(keyword in menu_item for keyword in category_keywords[item_category]):
                    ratio *= 1.2
                
                # Special handling for pasta dishes
                if item_category == 'pasta' and any(pasta_type in menu_item for pasta_type in ['spaghetti', 'penne', 'pici', 'risotto', 'pacchero', 'mezze']):
                    ratio *= 1.3
                
                # Special handling for pizza
                if item_category == 'pizza' and 'pizza' in menu_item:
                    ratio *= 1.4
                
                if ratio > best_ratio and ratio > 0.6:  # Much higher threshold
                    best_ratio = min(ratio, 1.0)
                    best_match = voce.copy()
                    best_match["sezione"] = section["nome"]

        return best_match if best_match else None

    def _extract_mentioned_dishes_from_history(self, conversation_history: List[Dict[str, str]]) -> List[str]:
        """
        Extract dish names mentioned by the waiter in conversation history.
        This helps when users reference dishes the waiter has already suggested.
        """
        mentioned_dishes = []
        
        if not conversation_history:
            return mentioned_dishes
        
        # Look through assistant messages (waiter responses)
        for message in conversation_history:
            if message.get("role") == "assistant":
                content = message.get("content", "").lower()
                
                # Extract dish names from menu that appear in waiter messages
                for section in self.menu.get("sezioni", []):
                    for item in section.get("voci", []):
                        dish_name = item.get("nome", "").lower()
                        # Look for exact dish name mentions in waiter responses
                        if dish_name in content and len(dish_name) > 3:  # Avoid short words
                            if dish_name not in mentioned_dishes:
                                mentioned_dishes.append(dish_name)
        
        return mentioned_dishes

    def _find_dish_in_conversation_history(self, requested_item: str, conversation_history: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """
        Check if the requested item matches a dish mentioned by the waiter in conversation history.
        If found, return the actual menu item.
        """
        if not conversation_history:
            return None
            
        mentioned_dishes = self._extract_mentioned_dishes_from_history(conversation_history)
        
        # Look for matches between requested item and mentioned dishes
        requested_lower = requested_item.lower()
        
        for dish_name in mentioned_dishes:
            # Check for partial matches or high similarity
            if (requested_lower in dish_name or 
                dish_name in requested_lower or 
                SequenceMatcher(None, requested_lower, dish_name).ratio() > 0.7):
                
                # Find the actual menu item
                for section in self.menu.get("sezioni", []):
                    for item in section.get("voci", []):
                        if item.get("nome", "").lower() == dish_name:
                            return {
                                "requested": requested_item,
                                "suggested": item["nome"],
                                "prezzo": item.get("prezzo", 0),
                                "sezione": section["nome"],
                                "from_history": True
                            }
        
        return None

    def _build_item_confirmation_message(self, extracted_items: List[str], suggestions: List[Dict]) -> str:
        """
        Build clarification message for item confirmation.
        """
        if not suggestions:
            return "Mi scusi, non ho trovato alcuni degli elementi che ha menzionato nel nostro menu. Può specificare meglio cosa desidera ordinare?"

        # Filter out suggestions with very low confidence
        good_suggestions = [s for s in suggestions if s.get('confidence', 0) > 0.5]
        
        if not good_suggestions:
            return "Mi scusi, non ho trovato corrispondenze appropriate nel menu per alcuni elementi. Può dirmi più precisamente cosa desidera?"

        message = "Ho interpretato la sua ordinazione, ma alcuni elementi potrebbero non essere nel menu. Intendeva:\n\n"

        for suggestion in good_suggestions:
            message += f"• Invece di '{suggestion['requested']}', intendeva '{suggestion['suggested']}' (€{suggestion['prezzo']})?\n"

        message += "\nConfermi o mi può aiutare a capire meglio?"
        return message