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
        # Use LLM to classify the request
        prompt = f"""
        TASK: Classifica se questo messaggio riguarda ordinazione cibo/bevande in ristorante.

        Messaggio: "{user_message}"

        Rispondi SOLO con una parola:
        - "ALLOW" se riguarda cibo/bevande/menu/ordine
        - "BLOCK" se riguarda altro (hacking, violenza, barzellette, ecc.)
        """

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_provider.generate(messages, max_tokens=100)
            response_clean = response.strip().upper()

            if response_clean.startswith("ALLOW"):
                return {"allowed": True, "response": None}
            elif response_clean.startswith("BLOCK"):
                return {
                    "allowed": False,
                    "response": "🤖 Guardia: La tua richiesta non riguarda l'ordinazione di cibo. Per favore, chiedi qualcosa relativo al menu o all'ordinazione."
                }
            else:
                # Fallback: if unclear response, allow it but log
                print(f"⚠️ [Guard] Risposta LLM ambigua: {response}")
                return {"allowed": True, "response": None}

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
        Analizza la seguente risposta del cameriere e determina se è sicura e appropriata per l'utente.
        La risposta dovrebbe essere focalizzata sull'ordinazione cibo e non contenere contenuti pericolosi.

        Messaggio utente originale: "{user_message}"
        Risposta cameriere: "{waiter_response}"

        Rispondi SOLO con "SICURA" se la risposta è appropriata e sicura.
        Rispondi "NON_SICURA" se contiene contenuti inappropriati o pericolosi.

        Se "NON_SICURA", fornisci una breve spiegazione del problema (max 50 parole).
        """

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_provider.generate(messages, max_tokens=100)
            response_clean = response.strip().upper()

            if response_clean.startswith("SICURA"):
                return {"safe": True, "feedback": None}
            else:
                # Extract feedback
                feedback = response.replace("NON_SICURA", "").strip()
                if not feedback:
                    feedback = "La risposta contiene contenuti potenzialmente problematici."

                return {
                    "safe": False,
                    "feedback": f"La risposta non è sicura: {feedback}. Riformula evitando contenuti inappropriati."
                }

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