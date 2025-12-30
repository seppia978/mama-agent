"""
Test avanzati per l'estrazione automatica dell'ordine in casi di dialogo naturale e conferme implicite.
"""
import json
import os
from dotenv import load_dotenv
from llm_provider import create_llm_provider
from waiter_agent import WaiterAgent

# Load environment variables
load_dotenv()

def load_menu(menu_path: str = "menu.json") -> dict:
    with open(menu_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def test_hard_cases():
    print("=" * 60)
    print("🧪 TEST AVANZATI ESTRAZIONE ORDINE")
    print("=" * 60)
    menu = load_menu("menu.json")
    llm_provider = create_llm_provider(
        "openai_compatible",
        model_name="gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY")
    )
    agent = WaiterAgent(menu, llm_provider)

    cases = [
        {
            "desc": "Conferma con 'aggiungilo' dopo suggerimento specifico",
            "dialog": [
                "Cosa mi consigli di pesce?",
                "Aggiungilo all'ordine!"
            ],
            "expected_min": 1  # Almeno 1 piatto di pesce
        },
        {
            "desc": "Conferma con 'ok' dopo suggerimento pizza",
            "dialog": [
                "Cosa mi consigli tra le pizze?",
                "Ok, va bene!"
            ],
            "expected_min": 1  # Almeno 1 pizza
        },
        {
            "desc": "Conferma con 'perfetto' dopo dolce",
            "dialog": [
                "Cos'hai per dessert?",
                "Perfetto, lo prendo!"
            ],
            "expected_min": 1  # Almeno 1 dolce
        },
        {
            "desc": "Ordine esplicito classico",
            "dialog": [
                "Prendo un cappuccino"
            ],
            "expected_exact": ["Cappuccino"]
        },
        {
            "desc": "Conferma dopo multiple opzioni",
            "dialog": [
                "Cosa mi consigli per colazione?",
                "Prendiamo tutto!"
            ],
            "expected_min": 2  # Almeno 2 piatti suggeriti
        }
    ]

    for i, case in enumerate(cases, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}: {case['desc']}")
        agent.reset_order()
        last_response = None
        for msg in case["dialog"]:
            last_response = agent.chat(msg)
        
        order_items = [item["item"]["nome"] for item in agent.get_order().items]
        print(f"Ordine estratto: {order_items}")
        
        # Check expectations
        success = False
        if "expected_exact" in case:
            print(f"Atteso esatto: {case['expected_exact']}")
            success = all(any(exp.lower() in o.lower() for o in order_items) for exp in case["expected_exact"])
        elif "expected_min" in case:
            print(f"Atteso minimo: {case['expected_min']} items")
            success = len(order_items) >= case["expected_min"]
        
        if success:
            print("✅ PASS")
        else:
            print("❌ FAIL")
            print(f"Ultima risposta: {last_response[:200]}...")

if __name__ == "__main__":
    test_hard_cases()
