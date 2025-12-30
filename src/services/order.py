"""
Order Manager - Gestione ordini cliente
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class OrderStatus(Enum):
    """Stati dell'ordine"""
    DRAFT = "draft"           # In composizione
    CONFIRMED = "confirmed"   # Confermato dal cliente
    SENT = "sent"             # Inviato in cucina
    COMPLETED = "completed"   # Completato


@dataclass
class OrderItem:
    """Singolo item nell'ordine"""
    id: str
    nome: str
    prezzo: float
    quantita: int = 1
    note: str = ""
    taglia: str = None

    @property
    def totale(self) -> float:
        return self.prezzo * self.quantita

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "prezzo": self.prezzo,
            "quantita": self.quantita,
            "note": self.note,
            "taglia": self.taglia,
            "totale": self.totale
        }


@dataclass
class CustomerPreferences:
    """Preferenze del cliente"""
    vegetariano: bool = False
    vegano: bool = False
    allergeni: List[int] = field(default_factory=list)
    intolleranze: List[str] = field(default_factory=list)
    note_speciali: str = ""

    def to_dict(self) -> Dict:
        return {
            "vegetariano": self.vegetariano,
            "vegano": self.vegano,
            "allergeni": self.allergeni,
            "intolleranze": self.intolleranze,
            "note_speciali": self.note_speciali
        }

    def has_restrictions(self) -> bool:
        return (
            self.vegetariano or
            self.vegano or
            len(self.allergeni) > 0 or
            len(self.intolleranze) > 0
        )

    def format_for_waiter(self) -> str:
        """Formatta le preferenze per il cameriere"""
        parts = []
        if self.vegetariano:
            parts.append("vegetariano")
        if self.vegano:
            parts.append("vegano")
        if self.intolleranze:
            parts.append(f"intolleranze: {', '.join(self.intolleranze)}")
        if self.note_speciali:
            parts.append(f"note: {self.note_speciali}")
        return " | ".join(parts) if parts else "nessuna preferenza specifica"


class OrderManager:
    """Gestisce l'ordine corrente del cliente"""

    def __init__(self):
        self.items: List[OrderItem] = []
        self.status: OrderStatus = OrderStatus.DRAFT
        self.preferences: CustomerPreferences = CustomerPreferences()
        self.created_at: datetime = datetime.now()
        self.notes: str = ""

    @property
    def totale(self) -> float:
        """Calcola totale ordine"""
        return sum(item.totale for item in self.items)

    @property
    def num_items(self) -> int:
        """Numero totale di item"""
        return sum(item.quantita for item in self.items)

    def add_item(
        self,
        id: str,
        nome: str,
        prezzo: float,
        quantita: int = 1,
        note: str = "",
        taglia: str = None
    ) -> OrderItem:
        """Aggiunge un item all'ordine"""
        # Cerca se esiste già
        for item in self.items:
            if item.id == id and item.taglia == taglia and item.note == note:
                item.quantita += quantita
                return item

        # Nuovo item
        new_item = OrderItem(
            id=id,
            nome=nome,
            prezzo=prezzo,
            quantita=quantita,
            note=note,
            taglia=taglia
        )
        self.items.append(new_item)
        return new_item

    def add_from_menu_item(self, menu_item: Dict, quantita: int = 1, note: str = "", taglia: str = None) -> OrderItem:
        """Aggiunge un item dal menu"""
        prezzo = menu_item.get("prezzo", 0)

        # Gestione taglie
        if taglia and "taglie" in menu_item:
            for t in menu_item["taglie"]:
                if t["nome"].lower() == taglia.lower():
                    prezzo = t["prezzo"]
                    break

        return self.add_item(
            id=menu_item.get("id", menu_item["nome"]),
            nome=menu_item["nome"],
            prezzo=prezzo,
            quantita=quantita,
            note=note,
            taglia=taglia
        )

    def remove_item(self, item_id: str, taglia: str = None) -> bool:
        """Rimuove un item dall'ordine"""
        for i, item in enumerate(self.items):
            if item.id == item_id and (taglia is None or item.taglia == taglia):
                self.items.pop(i)
                return True
        return False

    def update_quantity(self, item_id: str, quantita: int, taglia: str = None) -> bool:
        """Aggiorna quantità di un item"""
        for item in self.items:
            if item.id == item_id and (taglia is None or item.taglia == taglia):
                if quantita <= 0:
                    return self.remove_item(item_id, taglia)
                item.quantita = quantita
                return True
        return False

    def clear(self):
        """Svuota l'ordine"""
        self.items = []
        self.status = OrderStatus.DRAFT
        self.notes = ""

    def confirm(self):
        """Conferma l'ordine"""
        self.status = OrderStatus.CONFIRMED

    def send_to_kitchen(self):
        """Invia l'ordine in cucina"""
        self.status = OrderStatus.SENT

    def set_preference(self, key: str, value: Any):
        """Imposta una preferenza cliente"""
        if key == "vegetariano":
            self.preferences.vegetariano = bool(value)
        elif key == "vegano":
            self.preferences.vegano = bool(value)
        elif key == "allergeni":
            if isinstance(value, list):
                self.preferences.allergeni = value
            else:
                self.preferences.allergeni.append(value)
        elif key == "intolleranze":
            if isinstance(value, list):
                self.preferences.intolleranze = value
            elif value not in self.preferences.intolleranze:
                self.preferences.intolleranze.append(value)
        elif key == "note":
            self.preferences.note_speciali = str(value)

    def get_summary(self) -> str:
        """Ritorna riepilogo ordine"""
        if not self.items:
            return "Nessun ordine ancora."

        lines = ["**Il tuo ordine:**"]
        for item in self.items:
            nome = item.nome
            if item.taglia:
                nome += f" ({item.taglia})"
            if item.note:
                nome += f" - {item.note}"
            lines.append(f"- {nome} x{item.quantita} — €{item.totale:.2f}")

        lines.append(f"\n**Totale: €{self.totale:.2f}**")

        if self.preferences.has_restrictions():
            lines.append(f"\n_Preferenze: {self.preferences.format_for_waiter()}_")

        return "\n".join(lines)

    def get_summary_for_kitchen(self) -> str:
        """Ritorna riepilogo per la cucina"""
        lines = [f"ORDINE - {self.created_at.strftime('%H:%M')}"]

        if self.preferences.has_restrictions():
            lines.append(f"ATTENZIONE: {self.preferences.format_for_waiter()}")
            lines.append("")

        for item in self.items:
            line = f"{item.quantita}x {item.nome}"
            if item.taglia:
                line += f" ({item.taglia})"
            if item.note:
                line += f" [{item.note}]"
            lines.append(line)

        lines.append(f"\nTOTALE: €{self.totale:.2f}")
        return "\n".join(lines)

    def to_dict(self) -> Dict:
        """Serializza ordine"""
        return {
            "items": [item.to_dict() for item in self.items],
            "totale": self.totale,
            "status": self.status.value,
            "preferences": self.preferences.to_dict(),
            "created_at": self.created_at.isoformat(),
            "notes": self.notes
        }

    def is_empty(self) -> bool:
        """Verifica se l'ordine è vuoto"""
        return len(self.items) == 0
