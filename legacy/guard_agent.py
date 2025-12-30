"""
Guard Agent - Security layer between user and waiter agent
"""
from typing import Dict, Any, Optional
from llm_provider import LLMProvider


class GuardAgent:
    """
    Agent that monitors and filters user requests and waiter responses for safety and relevance.
    Ensures all interactions are focused on food ordering and prevents dangerous content.
    """

    def __init__(self, llm_provider: LLMProvider, menu: Dict[str, Any]):
        self.llm_provider = llm_provider
        self.menu = menu

    def check_user_request(self, user_message: str) -> Dict[str, Any]:
        """
        Check if user request is appropriate (food ordering related).
        Returns dict with 'allowed': bool, 'response': str (if blocked)
        """
        message_lower = user_message.lower().strip()
        
        # Whitelist: common conversation responses that are always allowed
        allowed_phrases = [
            'no', 'no grazie', 'sono a posto', 'basta così', 'va bene', 'ok', 'okay',
            'grazie', 'grazie mille', 'perfetto', 'bene', 'sì', 'sì grazie', 'certo',
            'non ordino altro', 'nient\'altro', 'solo questo', 'basta', 'stop',
            'ho finito', 'sono pronto', 'confermo', 'va bene così', 'tutto ok',
            'arrivederci', 'ciao', 'buona serata', 'buon appetito'
        ]
        
        # Check if message contains any allowed phrase
        for phrase in allowed_phrases:
            if phrase in message_lower:
                return {"allowed": True, "response": None}
        
        # For other messages, use LLM classification
        prompt = f"""
        Analizza il seguente messaggio dell'utente in un ristorante e determina se è APPROPRIATO nel contesto di una conversazione di ordinazione.

        CATEGORIE APPROPRIATE (permetti):
        - Ordinare cibo/bevande ("prendo pasta", "vorrei vino")
        - Chiedere consigli/menu ("cosa consigli?", "mostra menu")
        - Confermare/modificare ordine ("aggiungi acqua", "togli il dolce")
        - Chiedere informazioni sul ristorante/cucina ("siete aperti?", "ingredienti?")
        - Saluti e convenevoli normali ("ciao", "grazie", "arrivederci")

        CATEGORIE VIETATE (blocca):
        - Contenuti violenti o illegali
        - Insulti o linguaggio offensivo
        - Richieste di hacking/programmazione
        - Argomenti completamente scollegati dal ristorante
        - Spam o contenuti ripetitivi inappropriati

        Messaggio utente: "{user_message}"

        Rispondi SOLO con "ALLOW" o "BLOCK".
        """

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_provider.generate(messages, max_tokens=10)
            response_clean = response.strip().upper()

            if response_clean.startswith("ALLOW") or "ALLOW" in response_clean:
                return {"allowed": True, "response": None}
            else:
                return {
                    "allowed": False,
                    "response": "🤖 Guardia: La tua richiesta non riguarda l'ordinazione di cibo. Per favore, chiedi qualcosa relativo al menu o all'ordinazione."
                }

        except Exception as e:
            # Fallback: allow if LLM fails
            print(f"⚠️ [Guard] Errore nel controllo richiesta: {e}")
            return {"allowed": True, "response": None}

    def check_waiter_response(self, waiter_response: str, user_message: str) -> Dict[str, Any]:
        """
        Check if waiter response is safe for the user.
        Returns dict with 'safe': bool, 'feedback': str (if needs revision)
        """
        # This should rarely trigger, but check for any dangerous content
        prompt = f"""
        Analizza la seguente risposta del cameriere in un ristorante italiano.
        Determina se è SICURA e APPROPRIATA per l'utente.

        CATEGORIE APPROPRIATE (rispondi "ALLOW"):
        - Descrizioni di cibo e bevande
        - Consigli sul menu
        - Informazioni sui prezzi
        - Conferme di ordini
        - Domande chiarificatrici gentili
        - Risposte amichevoli e professionali

        CATEGORIE VIETATE (rispondi "BLOCK"):
        - Contenuti violenti o illegali
        - Linguaggio offensivo
        - Informazioni personali inappropriate
        - Contenuti politici o religiosi inappropriati
        - Qualsiasi cosa non correlata al ristorante

        Messaggio utente originale: "{user_message}"
        Risposta cameriere: "{waiter_response}"

        Rispondi SOLO con "ALLOW" o "BLOCK"
        """

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_provider.generate(messages, max_tokens=100)
            response_clean = response.strip().upper()

            if response_clean.startswith("ALLOW"):
                return {"safe": True, "feedback": None}
            elif response_clean.startswith("BLOCK"):
                return {
                    "safe": False,
                    "feedback": "La risposta contiene contenuti potenzialmente inappropriati."
                }
            else:
                # Fallback: assume safe if unclear
                print(f"⚠️ [Guard] Risposta LLM ambigua per waiter: {response}")
                return {"safe": True, "feedback": None}

        except Exception as e:
            # Fallback: assume safe if LLM fails
            print(f"⚠️ [Guard] Errore nel controllo risposta: {e}")
            return {"safe": True, "feedback": None}

    def process_user_message(self, user_message: str) -> Optional[str]:
        """
        Process user message through guard check.
        Returns the message if allowed, or guard response if blocked.
        """
        check_result = self.check_user_request(user_message)

        if check_result["allowed"]:
            return user_message  # Pass through to waiter
        else:
            return check_result["response"]  # Block and respond

    def process_waiter_response(self, waiter_response: str, user_message: str) -> str:
        """
        Process waiter response through guard check.
        Returns the response if safe, or triggers revision if not.
        """
        check_result = self.check_waiter_response(waiter_response, user_message)

        if check_result["safe"]:
            return waiter_response  # Pass through to user
        else:
            # This should trigger waiter to revise, but for now return feedback
            print(f"🚨 [Guard] Risposta waiter non sicura: {check_result['feedback']}")
            return f"🤖 Guardia: Ho rilevato un problema nella risposta. Riprova con una richiesta diversa."