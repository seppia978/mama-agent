#!/usr/bin/env python3
"""
Test script for SupervisorAgent functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supervisor_agent import SupervisorAgent
from llm_provider import create_llm_provider
import json

def load_menu():
    with open('menu.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def test_supervisor_agent():
    # Initialize
    menu = load_menu()
    llm_provider = create_llm_provider("ollama", model_name="llama3.2:3b")
    supervisor = SupervisorAgent(llm_provider, menu, tau=0.6)

    # Test cases
    test_messages = [
        "Vorrei ordinare spaghetti alla carbonara",  # Should be order, items exist
        "Che pizza consigli?",  # Might be order intent, low probability
        "Consigliami tre piatti da prendere per cena dal menu",  # Should be high probability
        "Buongiorno, come va?",  # Not an order
        "Prendo un'insalata di mare e vino rosso",  # Order with potentially non-existent item
        "Vorrei una pizza hawaiana",  # Order with non-existent item
    ]

    print("👁️ Test del Supervisor Agent")
    print("=" * 60)

    for msg in test_messages:
        print(f"\n💬 Messaggio: '{msg}'")
        analysis = supervisor.analyze_message(msg, [])  # Empty conversation history

        print(f"📊 Probabilità ordine: {analysis['order_probability']:.2f}")
        print(f"✅ È ordine: {analysis['is_order']}")
        print(f"🔍 Item estratti: {analysis['extracted_items']}")
        print(f"📋 Compliance menu: {analysis['menu_compliance']}")

        if analysis["needs_clarification"]:
            print(f"❓ Serve chiarimento: {analysis['clarification_type']}")
            print(f"💭 Messaggio chiarimento: {analysis['clarification_message'][:100]}...")

        if analysis["suggested_items"]:
            print(f"💡 Suggerimenti: {analysis['suggested_items']}")

def test_conversation_history_matching():
    """Test that supervisor can find dishes mentioned in conversation history"""
    menu = load_menu()
    llm_provider = create_llm_provider("ollama", model_name="llama3.2:3b")
    supervisor = SupervisorAgent(llm_provider, menu, tau=0.6)

    # Simulate conversation where waiter mentioned "Pici cacio, pepe e tartare di gambero rosso"
    conversation_history = [
        {"role": "user", "content": "Cosa consigli per primo?"},
        {"role": "assistant", "content": "Ti consiglio i Pici cacio, pepe e tartare di gambero rosso, sono eccellenti!"},
        {"role": "user", "content": "Prendo i pici"}
    ]

    print("\n🔄 Test Matching Cronologia Conversazione")
    print("=" * 60)
    
    # Test user referring to dish mentioned by waiter
    user_message = "Prendo i pici"
    analysis = supervisor.analyze_message(user_message, conversation_history)
    
    print(f"💬 Messaggio: '{user_message}'")
    print(f"📊 Probabilità ordine: {analysis['order_probability']:.2f}")
    print(f"✅ È ordine: {analysis['is_order']}")
    print(f"🔍 Item estratti: {analysis['extracted_items']}")
    print(f"📋 Compliance menu: {analysis['menu_compliance']}")
    
    if analysis["suggested_items"]:
        print(f"💡 Suggerimenti dalla cronologia: {analysis['suggested_items']}")
        # Check if suggestion comes from history
        for suggestion in analysis["suggested_items"]:
            if suggestion.get("from_history"):
                print(f"✅ Trovato nella cronologia: {suggestion['suggested']}")
            else:
                print(f"❌ Suggerimento dal menu: {suggestion['suggested']}")

if __name__ == "__main__":
    test_supervisor_agent()
    test_conversation_history_matching()
    test_conversation_history_matching()