"""
Test per verificare che le domande informative non aggiungano item all'ordine
"""
import json
from llm_provider import create_llm_provider
from waiter_agent import WaiterAgent


def load_menu(menu_path: str = "menu.json") -> dict:
    with open(menu_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_info_questions():
    print("=" * 60)
    print("🧪 TEST DOMANDE INFORMATIVE VS ORDINI")
    print("=" * 60)
    print()
    
    menu = load_menu("menu.json")
    llm_provider = create_llm_provider("ollama", model_name="llama3.2:1b")
    agent = WaiterAgent(menu, llm_provider)
    
    test_cases = [
        {
            "input": "Ciao vedo che nel menu c'è una voce chiamata 'pane, vino e zucchero' che significa?",
            "expected": "NON dovrebbe aggiungere",
            "should_add": False
        },
        {
            "input": "Cos'è il Pain Perdu?",
            "expected": "NON dovrebbe aggiungere",
            "should_add": False
        },
        {
            "input": "Quanto costa il cappuccino?",
            "expected": "NON dovrebbe aggiungere",
            "should_add": False
        },
        {
            "input": "Mi puoi dire cosa contiene lo yogurt?",
            "expected": "NON dovrebbe aggiungere",
            "should_add": False
        },
        {
            "input": "Vorrei un cappuccino",
            "expected": "DOVREBBE aggiungere",
            "should_add": True
        },
        {
            "input": "Prendo il Pain Perdu",
            "expected": "DOVREBBE aggiungere",
            "should_add": True
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}/{len(test_cases)}")
        print(f"Input: '{test['input']}'")
        print(f"Atteso: {test['expected']}")
        
        initial_count = len(agent.get_order().items)
        
        # Send message
        response = agent.chat(test['input'])
        
        final_count = len(agent.get_order().items)
        added = final_count > initial_count
        
        # Check result
        success = (added == test['should_add'])
        
        if success:
            print(f"✅ PASS - Item {'aggiunto' if added else 'NON aggiunto'} come previsto")
            passed += 1
        else:
            print(f"❌ FAIL - Item {'aggiunto' if added else 'NON aggiunto'} (atteso: {'aggiunto' if test['should_add'] else 'NON aggiunto'})")
            failed += 1
        
        print(f"Ordine: {final_count} items")
        
    print(f"\n{'='*60}")
    print(f"📊 RISULTATI FINALI")
    print(f"{'='*60}")
    print(f"✅ Passati: {passed}/{len(test_cases)}")
    print(f"❌ Falliti: {failed}/{len(test_cases)}")
    print(f"{'='*60}\n")
    
    # Show final order
    order = agent.get_order()
    if order.items:
        print("📝 Ordine finale:")
        print(order.get_summary())
    else:
        print("📝 Nessun item nell'ordine")


if __name__ == "__main__":
    test_info_questions()
