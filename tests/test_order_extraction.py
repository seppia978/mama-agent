"""
Test per verificare l'extraction automatica degli ordini
"""
import json
from llm_provider import create_llm_provider
from waiter_agent import WaiterAgent


def load_menu(menu_path: str = "menu.json") -> dict:
    """Load menu from JSON file"""
    with open(menu_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_order_extraction():
    """Test order extraction with various inputs"""
    
    print("=" * 60)
    print("🧪 TEST EXTRACTION ORDINI CON LLM")
    print("=" * 60)
    print()
    
    # Load menu and initialize
    menu = load_menu("menu.json")
    llm_provider = create_llm_provider("ollama", model_name="llama3.2:1b")
    agent = WaiterAgent(menu, llm_provider)
    
    # Test scenarios
    test_cases = [
        {
            "input": "Vorrei un caffè espresso per favore",
            "expected": "Dovrebbe aggiungere espresso"
        },
        {
            "input": "Cosa mi consigli per colazione?",
            "expected": "NON dovrebbe aggiungere nulla (solo domanda)"
        },
        {
            "input": "Perfetto, prendo uno yogurt grande con frutta",
            "expected": "Dovrebbe aggiungere yogurt grande"
        },
        {
            "input": "E poi anche un cappuccino",
            "expected": "Dovrebbe aggiungere cappuccino"
        },
        {
            "input": "Quanto costa il Pain Perdu?",
            "expected": "NON dovrebbe aggiungere (solo info)"
        },
        {
            "input": "Ok va bene, lo prendo",
            "expected": "Dovrebbe aggiungere Pain Perdu (dal contesto)"
        }
    ]
    
    print("🎬 INIZIO TEST\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}/6")
        print(f"Input: '{test_case['input']}'")
        print(f"Atteso: {test_case['expected']}")
        print()
        
        # Get response
        response = agent.chat(test_case['input'])
        print(f"🤖 Risposta: {response[:100]}...")
        
        # Check order
        order = agent.get_order()
        print(f"📝 Ordine attuale: {len(order.items)} items")
        if order.items:
            for item in order.items:
                print(f"   - {item['item']['nome']}: €{item['item'].get('prezzo', 0):.2f}")
        
        print("\n" + "-" * 60 + "\n")
    
    # Final summary
    print("=" * 60)
    print("📊 RIEPILOGO FINALE")
    print("=" * 60)
    
    final_order = agent.get_order()
    print(f"\n{final_order.get_summary()}\n")
    
    print(f"✅ Test completato!")
    print(f"Items nell'ordine: {len(final_order.items)}")
    print(f"Totale: €{final_order.total:.2f}")


if __name__ == "__main__":
    test_order_extraction()
