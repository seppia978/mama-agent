"""
Streamlit Web Interface for Virtual Waiter Agent - Clean ChatGPT-like Interface
A clean, user-friendly chat interface for ordering food, similar to ChatGPT
"""
import json
import streamlit as st
from pathlib import Path
import sys
import os
from dotenv import load_dotenv
from datetime import datetime

from llm_provider import create_llm_provider
from waiter_agent import WaiterAgent
from guard_agent import GuardAgent

# Load environment variables
load_dotenv()


# Page configuration - wide layout with centered chat
st.set_page_config(
    page_title="🍝 Cameriere Virtuale - Mama's Trattoria",
    page_icon="🍝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for ChatGPT-like styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        text-align: center;
        color: #E74C3C;
        margin-bottom: 0.5rem;
    }
    .stButton>button {
        width: 100%;
    }
    .stButton button[key^="suggestion_"] {
        width: auto !important;
        margin: 0 auto;
        display: block;
    }
    .suggestion-button {
        width: auto !important;
        margin: 0 auto;
        display: block;
        max-width: 90%;
        margin-left: auto;
        margin-right: auto;
        text-align: center;
    }
    .order-summary {
        background-color: #FFF8E1;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #E74C3C;
        color: #2C3E50 !important;
    }
    .order-summary h4 {
        color: #E74C3C !important;
        margin-top: 0;
    }
    .menu-item {
        background-color: #FFFFFF;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
        border: 1px solid #ECF0F1;
        color: #2C3E50;
    }
    .menu-item strong {
        color: #2C3E50;
        font-weight: 600;
    }
    .menu-item small {
        color: #7F8C8D !important;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        color: #212121;
        max-width: 90%;
        margin-left: auto;
        margin-right: auto;
        text-align: center;
    }
    .user-message {
        background-color: #E3F2FD;
        border-left: 4px solid #2196F3;
        text-align: right;
    }
    .assistant-message {
        background-color: #FFF3E0;
        border-left: 4px solid #FF9800;
        text-align: left;
    }
    .chat-container {
        max-height: 70vh;
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #ECF0F1;
        border-radius: 0.5rem;
        background-color: #FAFAFA;
        margin: 0 auto;
        width: 90%;
    }
    .chat-area {
        display: flex;
        flex-direction: column;
        align-items: center;
        width: 100%;
    }
    h3 {
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)


def load_menu(menu_path: str = "menu.json") -> dict:
    """Load menu from JSON file"""
    try:
        with open(menu_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"❌ File menu non trovato: {menu_path}")
        st.stop()
    except json.JSONDecodeError as e:
        st.error(f"❌ Errore nel parsing del menu JSON: {e}")
        st.stop()


@st.cache_resource
def initialize_agent():
    """Initialize the LLM provider and agents (cached) - Fixed to Ollama with llama3.2:3b"""
    try:
        # Load menu
        menu = load_menu()
        
        # Fixed provider: Ollama with llama3.2:3b
        llm_provider = create_llm_provider("ollama", model_name="llama3.2:3b")
        
        # Initialize guard agent
        guard = GuardAgent(llm_provider, menu)
        
        # Initialize waiter agent
        waiter = WaiterAgent(menu, llm_provider)
        
        return {"guard": guard, "waiter": waiter, "menu": menu}
    except Exception as e:
        st.error(f"❌ Errore nell'inizializzazione: {e}")
        st.stop()


def display_menu(menu: dict):
    """Display the restaurant menu in a nice format"""
    st.markdown(f"### 📋 Menu - {menu.get('ristorante', 'Ristorante')}")
    if 'edizione' in menu:
        st.caption(f"{menu['edizione']} - {menu.get('luogo', '')}")
    
    # Support both old format (categorie) and new format (sezioni)
    sections = menu.get("sezioni", [])
    if sections:
        # New format with sezioni
        for sezione in sections:
            with st.expander(f"🔸 {sezione['nome'].upper()}", expanded=False):
                for item in sezione.get('voci', []):
                    # Handle items with sizes
                    if 'taglie' in item:
                        sizes_text = " | ".join([f"{t['nome']}: €{t['prezzo']:.2f}" for t in item['taglie']])
                        st.markdown(f"""
                            <div class="menu-item">
                                <strong>{item['nome']}</strong><br>
                                <small style="color: #E74C3C;">{sizes_text}</small><br>
                                <small style="color: #7F8C8D;">{item.get('descrizione', '')}</small>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        prezzo = item.get('prezzo')
                        if prezzo is not None:
                            st.markdown(f"""
                                <div class="menu-item">
                                    <strong>{item['nome']}</strong> - €{prezzo:.2f}<br>
                                    <small style="color: #7F8C8D;">{item.get('descrizione', '')}</small>
                                </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                                <div class="menu-item">
                                    <strong>{item['nome']}</strong><br>
                                    <small style="color: #7F8C8D;">{item.get('descrizione', '')}</small>
                                </div>
                            """, unsafe_allow_html=True)
    else:
        # Old format with categorie
        for categoria, items in menu.get("categorie", {}).items():
            with st.expander(f"🔸 {categoria.upper()}", expanded=False):
                for item in items:
                    st.markdown(f"""
                        <div class="menu-item">
                            <strong>{item['nome']}</strong> - €{item['prezzo']:.2f}<br>
                            <small style="color: #7F8C8D;">{item['descrizione']}</small>
                        </div>
                    """, unsafe_allow_html=True)


def display_order_summary(agent: WaiterAgent):
    """Display current order summary with item removal"""
    order = agent.get_order()
    
    # Always show order box, even if empty
    st.markdown('<div class="order-summary"><h4>📝 Il Tuo Ordine</h4></div>', unsafe_allow_html=True)
    
    if order.items or order.special_requests:
        # Display each item with remove button
        for idx, order_item in enumerate(order.items):
            item = order_item["item"]
            qty = order_item["quantity"]
            col1, col2 = st.columns([4, 1])
            
            with col1:
                item_text = f"{item['nome']} x{qty} (€{item['prezzo'] * qty:.2f})"
                if item.get('custom'):
                    item_text += " ⚠️"
                st.write(item_text)
            
            with col2:
                if st.button("❌", key=f"remove_{idx}_{item.get('id', item['nome'])}"):
                    item_id = item.get('id', item['nome'])
                    agent.order.remove_item(item_id)
                    st.rerun()
        
        # Display total
        st.markdown(f"**Totale: €{order.total:.2f}**")
        
        # Send order button
        if st.button("✅ Invia Ordine"):
            st.success("Ordine inviato alla cucina! 🍽️")
            agent.reset_order()
            st.rerun()
    else:
        st.markdown("""
        <div style="text-align: center; color: #7F8C8D; padding: 1rem;">
            🛒 Il tuo carrello è vuoto<br>
            <small>Aggiungi piatti dalla chat!</small>
        </div>
        """, unsafe_allow_html=True)


def main():
    # Header
    st.markdown('<p class="main-header">🍝 Cameriere Virtuale</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header" style="text-align: center; color: #7F8C8D;">Mama\'s Trattoria - Il tuo assistente personale per ordinare</p>', unsafe_allow_html=True)
    
    # Sidebar with menu and order
    with st.sidebar:
        # Initialize agents and menu for sidebar
        if 'agents' not in st.session_state:
            with st.spinner("🤖 Inizializzazione agenti virtuali..."):
                agents = initialize_agent()
                st.session_state.agents = agents
        
        guard = st.session_state.agents['guard']
        waiter = st.session_state.agents['waiter']
        menu = st.session_state.agents['menu']
        
        # For backward compatibility, also set agent to waiter
        agent = waiter
        
        # Display order summary in sidebar
        st.markdown("### 📝 Il Tuo Ordine")
        display_order_summary(agent)
        
        st.markdown("---")
        
        # Display menu in sidebar
        display_menu(menu)
        
        st.markdown("---")
        
        # Quick actions
        st.markdown("## 🎯 Azioni Rapide")
        
        if st.button("🔄 Reset Ordine"):
            agent.reset_order()
            st.success("✅ Ordine azzerato!")
            st.rerun()
        
        if st.button("🗑️ Cancella Chat"):
            st.session_state.messages = []
            st.success("✅ Chat cancellata!")
            st.rerun()
    
    # Main chat area - ChatGPT-like
    st.markdown('<div class="chat-area">', unsafe_allow_html=True)
    
    # Quick suggestion button based on time
    hour = datetime.now().hour
    if hour < 11:
        advice = "Suggerimenti per la colazione"
        prompt = "Consigliami tre piatti da prendere per colazione dal menu."
    elif hour < 16:
        advice = "Suggerimenti per il pranzo"
        prompt = "Consigliami tre piatti da prendere per pranzo dal menu."
    else:
        advice = "Suggerimenti per la cena"
        prompt = "Consigliami tre piatti da prendere per cena dal menu."

    st.markdown('<div style="text-align: center; margin-bottom: 1rem;">', unsafe_allow_html=True)
    button_key = f"suggestion_{hour}"
    if st.button(f"💡 {advice}", key=button_key):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.thinking = True
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Add welcome message
        welcome_msg = "👋 Benvenuto! Sono il tuo cameriere virtuale. Come posso aiutarti oggi? Vuoi vedere il menu o preferisci che ti consigli qualcosa?\\nPremi il pulsante di suggerimento per ricevere consigli veloci."
        st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
    
    # Display chat messages in a scrollable container
    # st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>👤 Tu:</strong><br>
                    {message["content"]}
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="chat-message assistant-message">
                    <strong>🧑‍🍳 Cameriere:</strong><br>
                    {message["content"]}
                </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat input at the bottom
    user_input = st.chat_input("Scrivi qui il tuo messaggio...")
    
    if user_input:
        # Add user message to chat immediately
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.thinking = True
        st.rerun()
    
    # Handle thinking after message is displayed
    if st.session_state.get('thinking', False):
        with st.spinner("🧑‍🍳 Il cameriere sta pensando..."):
            try:
                # Get the last user message
                last_user_message = st.session_state.messages[-1]["content"]
                
                # First, check user message with guard
                guarded_message = guard.process_user_message(last_user_message)
                
                if guarded_message == last_user_message:
                    # Message allowed, proceed with waiter
                    response = waiter.chat(last_user_message)
                    
                    # Check waiter response with guard
                    final_response = guard.process_waiter_response(response, last_user_message)
                else:
                    # Message blocked by guard
                    final_response = guarded_message
                
                st.session_state.messages.append({"role": "assistant", "content": final_response})
            except Exception as e:
                error_msg = f"❌ Errore: {str(e)}"
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
        st.session_state.thinking = False
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()