"""
Test script per il cameriere virtuale con il nuovo menu
"""
import json
from llm_provider import create_llm_provider
from waiter_agent import WaiterAgent


def load_menu(menu_path: str = "menu.json") -> dict:
    """Load menu from JSON file"""
    with open(menu_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_conversation():
    """Test a conversation with the waiter agent"""
    
    print("=" * 60)
    print("🍝 TEST CAMERIERE VIRTUALE - MAMA Arts & Bistrot")
    print("=" * 60)
    print()
    
    # Load menu
    print("📂 Caricamento menu...")
    menu = load_menu("menu.json")
    print(f"✅ Menu caricato: {menu['ristorante']}")
    print(f"   Edizione: {menu['edizione']}")
    print(f"   Luogo: {menu['luogo']}")
    print()
    
    # Initialize LLM
    print("🤖 Inizializzazione LLM (Ollama con llama3.2:1b)...")
    llm_provider = create_llm_provider("ollama", model_name="llama3.2:1b")
    print("✅ LLM pronto!")
    print()
    
    # Initialize agent
    print("👨‍🍳 Inizializzazione cameriere...")
    agent = WaiterAgent(menu, llm_provider)
    print("✅ Cameriere pronto!")
    print()
    
    # Test conversation
    test_messages = [
        "Ciao! Cosa mi consigli per colazione?",
        "Ho voglia di qualcosa dolce",
        "Perfetto, prendo uno yogurt grande con frutta",
        "E poi anche un caffè filtro V60",
        "Quanto viene in totale?"
    ]
    
    print("=" * 60)
    print("💬 INIZIO CONVERSAZIONE TEST")
    print("=" * 60)
    print()
    
    for i, user_msg in enumerate(test_messages, 1):
        print(f"👤 Cliente: {user_msg}")
        
        try:
            response = agent.chat(user_msg)
            print(f"🧑‍🍳 Cameriere: {response}")
        except Exception as e:
            print(f"❌ Errore: {e}")
        
        print()
        
        # Show order after each interaction
        if i >= 3:  # Show order after ordering items
            order = agent.get_order()
            if order.items:
                print("📝 Ordine corrente:")
                print(order.get_summary())
                print()
    
    print("=" * 60)
    print("✅ TEST COMPLETATO")
    print("=" * 60)
    
    # Final order summary
    final_order = agent.get_order()
    if final_order.items:
        print()
        print("📋 ORDINE FINALE:")
        print(final_order.get_summary())
        print()
        print(f"💰 Totale: €{final_order.total:.2f}")


if __name__ == "__main__":
    test_conversation()
