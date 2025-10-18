"""
Main application for the Virtual Waiter Agent
"""
import json
import sys
from pathlib import Path
from typing import Optional
import argparse

from llm_provider import create_llm_provider
from waiter_agent import WaiterAgent


def load_menu(menu_path: str) -> dict:
    """Load menu from JSON file"""
    try:
        with open(menu_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Errore: File menu non trovato: {menu_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Errore nel parsing del menu JSON: {e}")
        sys.exit(1)


def print_welcome():
    """Print welcome message"""
    print("=" * 60)
    print("🍝 CAMERIERE VIRTUALE - Mama's Trattoria")
    print("=" * 60)
    print("\nBenvenuto! Sono il tuo cameriere virtuale.")
    print("Parla con me come faresti con un vero cameriere!")
    print("\nComandi speciali:")
    print("  • 'menu' - Visualizza il menu completo")
    print("  • 'ordine' - Visualizza il tuo ordine corrente")
    print("  • 'reset' - Ricomincia l'ordine da capo")
    print("  • 'esci' o 'quit' - Termina la conversazione")
    print("=" * 60)
    print()


def print_menu(menu: dict):
    """Print formatted menu"""
    print("\n" + "=" * 60)
    print(f"📋 MENU - {menu['ristorante']}")
    print("=" * 60)

    for categoria, items in menu["categorie"].items():
        print(f"\n{categoria.upper()}")
        print("-" * 40)
        for item in items:
            print(f"\n{item['nome']} - {item['prezzo']:.2f}€")
            print(f"  {item['descrizione']}")
            if "suggerimenti" in item:
                print(f"  💡 {item['suggerimenti']}")
            tags = []
            if item.get("vegetariano"):
                tags.append("🌱 VEGETARIANO")
            if item.get("vegano"):
                tags.append("🌿 VEGANO")
            if tags:
                print(f"  {' '.join(tags)}")
            if item.get("allergeni"):
                print(f"  ⚠️  Allergeni: {', '.join(item['allergeni'])}")

    print("\n" + "=" * 60 + "\n")


def run_interactive_mode(agent: WaiterAgent, menu: dict):
    """Run interactive conversation mode"""
    print_welcome()

    # Initial greeting from the waiter
    initial_greeting = agent.chat("Ciao!")
    print(f"\n🧑‍🍳 Cameriere: {initial_greeting}\n")

    while True:
        try:
            # Get user input
            user_input = input("👤 Tu: ").strip()

            if not user_input:
                continue

            # Handle special commands
            user_input_lower = user_input.lower()

            if user_input_lower in ['esci', 'quit', 'exit', 'bye']:
                order = agent.get_order()
                if order.items:
                    print(f"\n📝 {order.get_summary()}")
                    print("\n🧑‍🍳 Cameriere: Grazie per la tua ordinazione! A presto!")
                else:
                    print("\n🧑‍🍳 Cameriere: Grazie della visita! Torna presto!")
                break

            elif user_input_lower == 'menu':
                print_menu(menu)
                continue

            elif user_input_lower == 'ordine':
                order = agent.get_order()
                print(f"\n📝 {order.get_summary()}\n")
                continue

            elif user_input_lower == 'reset':
                agent.reset_order()
                print("\n✅ Ordine azzerato!\n")
                continue

            # Process message with agent
            response = agent.chat(user_input)
            print(f"\n🧑‍🍳 Cameriere: {response}\n")

        except KeyboardInterrupt:
            print("\n\n🧑‍🍳 Cameriere: Arrivederci!")
            break
        except Exception as e:
            print(f"\n❌ Errore: {e}\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Virtual Waiter Agent powered by LLM")
    parser.add_argument(
        "--menu",
        type=str,
        default="menu.json",
        help="Path to menu JSON file (default: menu.json)"
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="ollama",
        choices=["ollama", "huggingface", "openai_compatible"],
        help="LLM provider to use (default: ollama)"
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Model name (provider-specific)"
    )
    parser.add_argument(
        "--base-url",
        type=str,
        help="Base URL for API providers"
    )

    args = parser.parse_args()

    # Load menu
    print("📂 Caricamento menu...")
    menu = load_menu(args.menu)

    # Initialize LLM provider
    print(f"🤖 Inizializzazione LLM provider ({args.provider})...")

    provider_kwargs = {}
    if args.model:
        provider_kwargs["model_name"] = args.model
    if args.base_url:
        provider_kwargs["base_url"] = args.base_url

    try:
        llm_provider = create_llm_provider(args.provider, **provider_kwargs)
        print("✅ LLM provider pronto!\n")
    except Exception as e:
        print(f"❌ Errore nell'inizializzazione del provider LLM: {e}")
        print("\n💡 Suggerimenti:")
        if args.provider == "ollama":
            print("   - Assicurati che Ollama sia in esecuzione: ollama serve")
            print("   - Scarica il modello: ollama pull llama3.1:8b-instruct-q4_K_M")
        elif args.provider == "huggingface":
            print("   - Assicurati di avere un token Hugging Face valido")
            print("   - Accetta i termini per Llama su huggingface.co")
        sys.exit(1)

    # Initialize waiter agent
    print("👨‍🍳 Inizializzazione cameriere virtuale...")
    agent = WaiterAgent(menu, llm_provider)

    # Run interactive mode
    run_interactive_mode(agent, menu)


if __name__ == "__main__":
    main()
