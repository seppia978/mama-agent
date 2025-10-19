"""
Streamlit Web Interface for Virtual Waiter Agent
A beautiful and interactive chat interface for ordering food
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

# Load environment variables
load_dotenv()


# Page configuration
st.set_page_config(
    page_title="🍝 Cameriere Virtuale - Mama's Trattoria",
    page_icon="🍝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #E74C3C;
        margin-bottom: 1rem;
    }
    .sub-header {
        text-align: center;
        color: #7F8C8D;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
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
    }
    .user-message {
        background-color: #E3F2FD;
        border-left: 4px solid #2196F3;
        color: #1565C0;
    }
    .assistant-message {
        background-color: #FFF3E0;
        border-left: 4px solid #FF9800;
        color: #E65100;
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
def initialize_agent(provider_type: str = "ollama", model_name: str = None, api_key: str = None):
    """Initialize the LLM provider and waiter agent (cached)"""
    try:
        # Load menu
        menu = load_menu()
        
        # Initialize LLM provider
        provider_kwargs = {}
        if model_name:
            provider_kwargs["model_name"] = model_name
        if api_key:
            provider_kwargs["api_key"] = api_key
        
        llm_provider = create_llm_provider(provider_type, **provider_kwargs)
        
        # Initialize waiter agent
        agent = WaiterAgent(menu, llm_provider)
        
        return agent, menu
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
    """Display current order summary"""
    order = agent.get_order()
    summary_text = order.get_summary()
    if order.items or order.special_requests:
        st.markdown(f"""
            <div class="order-summary">
                <h4>📝 Il Tuo Ordine</h4>
                {summary_text.replace('\n', '<br>')}
            </div>
        """, unsafe_allow_html=True)
        if st.button("✅ Invia Ordine"):
            st.success("Ordine inviato alla cucina! 🍽️")
            agent.reset_order()
            st.rerun()
    else:
        st.info("🛒 Il tuo carrello è vuoto")


def main():
    # Header
    st.markdown('<p class="main-header">🍝 Cameriere Virtuale</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Mama\'s Trattoria - Il tuo assistente personale per ordinare</p>', unsafe_allow_html=True)
    
    # Sidebar configuration
    with st.sidebar:
        st.markdown("## ⚙️ Configurazione")
        
        provider = st.selectbox(
            "Provider LLM",
            ["ollama", "openai_compatible", "huggingface"],
            index=1 if os.getenv("OPENAI_API_KEY") else 0,
            help="Seleziona il provider per il modello linguistico"
        )
        
        if provider == "ollama":
            model_name = st.text_input(
                "Nome Modello",
                value="llama3.2:3b",
                help="Nome del modello Ollama (es. llama3.2:3b, llama3.1:8b)"
            )
            api_key = None
        elif provider == "openai_compatible":
            # Check if API key exists in .env
            env_api_key = os.getenv("OPENAI_API_KEY")
            if env_api_key:
                st.success("✅ API Key caricata da .env")
                api_key = env_api_key
                model_name = st.text_input(
                    "Nome Modello",
                    value=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    help="Nome del modello OpenAI"
                )
            else:
                api_key = st.text_input(
                    "OpenAI API Key",
                    type="password",
                    help="Inserisci la tua API key di OpenAI"
                )
                model_name = st.text_input(
                    "Nome Modello",
                    value="gpt-4o-mini",
                    help="Nome del modello OpenAI"
                )
        else:
            model_name = None
            api_key = None
        
        st.markdown("---")
        st.markdown("## 📖 Come Usare")
        st.markdown("""
        1. 👋 Saluta il cameriere
        2. 💬 Chiedi consigli o ordina
        3. 📝 Controlla il tuo ordine
        4. 🔄 Resetta quando vuoi ricominciare
        """)
        
        st.markdown("---")
        st.markdown("## 🎯 Comandi Rapidi")
        
        if st.button("🔄 Reset Ordine"):
            if 'agent' in st.session_state:
                st.session_state.agent.reset_order()
                st.success("✅ Ordine azzerato!")
                st.rerun()
        
        if st.button("🗑️ Cancella Chat"):
            st.session_state.messages = []
            st.success("✅ Chat cancellata!")
            st.rerun()
    
    # Initialize agent (cached)
    if 'agent' not in st.session_state or 'menu' not in st.session_state:
        with st.spinner("🤖 Inizializzazione cameriere virtuale..."):
            agent, menu = initialize_agent(provider, model_name, api_key)
            st.session_state.agent = agent
            st.session_state.menu = menu
    
    agent = st.session_state.agent
    menu = st.session_state.menu
    
    # Create two columns
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 💬 Chat con il Cameriere")

        # Pulsante rapido suggerimenti in base all'orario
        hour = datetime.now().hour
        if hour < 11:
            advice = "Suggerimenti per la colazione"
            prompt = "Cosa mi consigli per la colazione?"
        elif hour < 16:
            advice = "Suggerimenti per il pranzo"
            prompt = "Cosa mi consigli per il pranzo?"
        else:
            advice = "Suggerimenti per la cena"
            prompt = "Cosa mi consigli per la cena?"
        if st.button(f"💡 {advice}"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            # Genera subito la risposta del cameriere
            with st.spinner("🧑‍🍳 Il cameriere sta pensando..."):
                try:
                    response = agent.chat(prompt)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"❌ Errore: {str(e)}"
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
            st.rerun()

        # Initialize chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []
            # Add welcome message
            welcome_msg = "👋 Benvenuto! Sono il tuo cameriere virtuale. Come posso aiutarti oggi? Vuoi vedere il menu o preferisci che ti consigli qualcosa?"
            st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
        
        # Display chat messages
        chat_container = st.container()
        with chat_container:
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
        
        # Chat input
        user_input = st.chat_input("Scrivi qui il tuo messaggio...")
        
        if user_input:
            # Add user message to chat
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Get response from agent
            with st.spinner("🧑‍🍳 Il cameriere sta pensando..."):
                try:
                    response = agent.chat(user_input)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"❌ Errore: {str(e)}"
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
            
            # Rerun to update the chat
            st.rerun()
    
    with col2:
        # Display order summary
        st.markdown("### 📝 Il Tuo Ordine")
        display_order_summary(agent)
        
        st.markdown("---")
        
        # Display menu
        with st.expander("📖 Visualizza Menu Completo", expanded=False):
            display_menu(menu)
        
        st.markdown("---")
        
        # Statistics
        st.markdown("### 📊 Statistiche")
        order = agent.get_order()
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Piatti", len(order.items))
        with col_b:
            st.metric("Totale", f"€{order.total:.2f}")


if __name__ == "__main__":
    main()
