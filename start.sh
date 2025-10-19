#!/bin/bash

# MAMA Arts & Bistrot - Virtual Waiter Launcher
# Quick start script

echo "🍝 MAMA Arts & Bistrot - Virtual Waiter"
echo "========================================"
echo ""

# Check if Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "⚠️  Ollama non è in esecuzione. Avvio in corso..."
    brew services start ollama
    sleep 3
fi

# Check if model is available
if ! ollama list | grep -q "llama3.2:1b"; then
    echo "📦 Modello llama3.2:1b non trovato. Download in corso..."
    ollama pull llama3.2:1b
fi

echo ""
echo "✅ Tutto pronto!"
echo ""
echo "Scegli l'interfaccia:"
echo "  1) Streamlit Web App (Consigliato)"
echo "  2) CLI Interattiva"
echo ""
read -p "Scelta (1 o 2): " choice

case $choice in
    1)
        echo ""
        echo "🌐 Avvio interfaccia web..."
        streamlit run streamlit_app.py
        ;;
    2)
        echo ""
        echo "💻 Avvio CLI..."
        python3 main.py
        ;;
    *)
        echo "❌ Scelta non valida"
        exit 1
        ;;
esac
