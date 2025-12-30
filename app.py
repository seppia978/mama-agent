"""
MAMA Virtual Waiter - Streamlit Application
Interfaccia utente per il cameriere virtuale
"""
import streamlit as st
import os
from dotenv import load_dotenv

from src.core.llm import create_provider
from src.services.menu import MenuService
from src.services.order import OrderManager
from src.agents.waiter import WaiterAgent

# Load environment
load_dotenv()

# Page config
st.set_page_config(
    page_title="MAMA - Cameriere Virtuale",
    page_icon="🍝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Header */
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(135deg, #D32F2F 0%, #FF5722 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .main-header h1 {
        margin: 0;
        font-size: 2rem;
    }
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }

    /* Chat messages */
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        max-width: 85%;
    }
    .user-message {
        background: #E3F2FD;
        border-left: 4px solid #1976D2;
        margin-left: auto;
        text-align: left;
    }
    .assistant-message {
        background: #FFF3E0;
        border-left: 4px solid #FF9800;
    }

    /* Order panel */
    .order-panel {
        background: #FFFDE7;
        padding: 1rem;
        border-radius: 10px;
        border: 2px solid #FFC107;
    }
    .order-panel h3 {
        color: #F57F17;
        margin-top: 0;
    }

    /* Menu section */
    .menu-section {
        background: #FAFAFA;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.25rem 0;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 20px;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def initialize_waiter():
    """Inizializza il cameriere virtuale"""
    try:
        # LLM Provider
        llm = create_provider("openai", model="gpt-4o")

        # Menu Service
        menu = MenuService("menu.json")

        # Order Manager
        order = OrderManager()

        # Waiter Agent
        waiter = WaiterAgent(llm, menu, order)

        return waiter, menu
    except Exception as e:
        st.error(f"Errore inizializzazione: {e}")
        st.stop()


def render_header(menu: MenuService):
    """Renderizza header"""
    st.markdown(f"""
    <div class="main-header">
        <h1>🍝 {menu.get_restaurant_name()}</h1>
        <p>Il tuo cameriere virtuale</p>
    </div>
    """, unsafe_allow_html=True)


def render_order_panel(waiter: WaiterAgent):
    """Renderizza pannello ordine nella sidebar"""
    st.markdown("### 🛒 Il Tuo Ordine")

    if waiter.order.is_empty():
        st.info("Il carrello è vuoto")
    else:
        for item in waiter.order.items:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                nome = item.nome
                if item.taglia:
                    nome += f" ({item.taglia})"
                st.write(f"**{nome}**")
            with col2:
                st.write(f"x{item.quantita}")
            with col3:
                if st.button("❌", key=f"rm_{item.id}"):
                    waiter.order.remove_item(item.id)
                    st.rerun()

        st.markdown("---")
        st.markdown(f"### Totale: €{waiter.order.totale:.2f}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Svuota", use_container_width=True):
                waiter.clear_order()
                st.rerun()
        with col2:
            if st.button("✅ Conferma", type="primary", use_container_width=True):
                st.success("Ordine confermato!")
                st.balloons()


def render_menu_browser(menu: MenuService):
    """Renderizza browser del menu"""
    st.markdown("### 📖 Menu")

    for section in menu.get_sections():
        with st.expander(f"🔸 {section}"):
            items = menu.get_items_by_section(section)
            for item in items:
                if item.taglie:
                    sizes = " | ".join([f"{t['nome']}: €{t['prezzo']:.2f}" for t in item.taglie])
                    st.markdown(f"**{item.nome}**: {sizes}")
                elif item.prezzo:
                    st.markdown(f"**{item.nome}** — €{item.prezzo:.2f}")
                else:
                    st.markdown(f"**{item.nome}**")

                if item.descrizione:
                    st.caption(item.descrizione)


def render_quick_actions():
    """Renderizza azioni rapide"""
    st.markdown("### 💡 Suggerimenti")

    suggestions = [
        ("🥗 Piatti vegetariani", "Quali piatti vegetariani avete?"),
        ("🍷 Abbinamento vino", "Che vino mi consigli?"),
        ("🎂 Dolci", "Cosa avete come dolce?"),
        ("⭐ Consiglio chef", "Qual è il piatto del giorno?"),
    ]

    for label, prompt in suggestions:
        if st.button(label, use_container_width=True, key=f"sugg_{label}"):
            st.session_state.pending_message = prompt
            st.rerun()


def render_chat(waiter: WaiterAgent):
    """Renderizza area chat principale"""

    # Inizializza cronologia se non esiste
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Messaggio di benvenuto
        welcome = "👋 Benvenuto! Sono il tuo cameriere virtuale. Come posso aiutarti oggi?\n\nPuoi chiedermi consigli sul menu, informazioni sui piatti o iniziare direttamente a ordinare!"
        st.session_state.messages.append({"role": "assistant", "content": welcome})

    # Mostra messaggi
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>👤 Tu:</strong><br>{msg["content"]}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-message assistant-message">
                <strong>🧑‍🍳 Cameriere:</strong><br>{msg["content"]}
            </div>
            """, unsafe_allow_html=True)

    # Input utente
    user_input = st.chat_input("Scrivi qui...")

    # Gestisci messaggio pendente dai suggerimenti
    if "pending_message" in st.session_state:
        user_input = st.session_state.pending_message
        del st.session_state.pending_message

    if user_input:
        # Aggiungi messaggio utente
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Genera risposta
        with st.spinner("🧑‍🍳 Il cameriere sta pensando..."):
            response = waiter.chat(user_input)

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()


def main():
    """Main app"""
    # Inizializza
    waiter, menu = initialize_waiter()

    # Header
    render_header(menu)

    # Layout: sidebar + main
    with st.sidebar:
        render_order_panel(waiter)
        st.markdown("---")
        render_menu_browser(menu)
        st.markdown("---")
        render_quick_actions()

        # Reset
        st.markdown("---")
        if st.button("🔄 Nuova conversazione", use_container_width=True):
            waiter.reset()
            st.session_state.messages = []
            st.rerun()

    # Main chat
    render_chat(waiter)


if __name__ == "__main__":
    main()
