"""
Menu Service - Gestione menu del ristorante
"""
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MenuItem:
    """Rappresenta un elemento del menu"""
    id: str
    nome: str
    prezzo: float
    sezione: str
    descrizione: str = ""
    allergeni: List[int] = None
    vegetariano: bool = False
    vegano: bool = False
    taglie: List[Dict] = None

    def __post_init__(self):
        if self.allergeni is None:
            self.allergeni = []
        if self.taglie is None:
            self.taglie = []

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "prezzo": self.prezzo,
            "sezione": self.sezione,
            "descrizione": self.descrizione,
            "allergeni": self.allergeni,
            "vegetariano": self.vegetariano,
            "vegano": self.vegano,
            "taglie": self.taglie
        }


class MenuService:
    """Servizio per gestione e ricerca nel menu"""

    def __init__(self, menu_path: str = "data/menu.json"):
        self.menu_path = menu_path
        self.raw_menu: Dict = {}
        self.items: List[MenuItem] = []
        self.allergeni_legend: Dict[str, str] = {}
        self._load_menu()

    def _load_menu(self):
        """Carica il menu da file JSON"""
        path = Path(self.menu_path)
        if not path.exists():
            # Fallback to root menu.json
            path = Path("menu.json")

        with open(path, 'r', encoding='utf-8') as f:
            self.raw_menu = json.load(f)

        self.allergeni_legend = self.raw_menu.get("allergeni_legend", {})
        self._parse_menu()

    def _parse_menu(self):
        """Parsa il menu in oggetti MenuItem"""
        self.items = []

        for sezione in self.raw_menu.get("sezioni", []):
            sezione_nome = sezione["nome"]

            for voce in sezione.get("voci", []):
                # Determina prezzo (gestisce taglie)
                if "taglie" in voce:
                    prezzo = voce["taglie"][0]["prezzo"] if voce["taglie"] else 0
                else:
                    prezzo = voce.get("prezzo", 0) or 0

                item = MenuItem(
                    id=voce.get("id", voce["nome"]),
                    nome=voce["nome"],
                    prezzo=prezzo,
                    sezione=sezione_nome,
                    descrizione=voce.get("descrizione", ""),
                    allergeni=voce.get("allergeni", []),
                    vegetariano="(V)" in voce["nome"] or voce.get("vegetariano", False),
                    vegano="(VG)" in voce["nome"] or voce.get("vegano", False),
                    taglie=voce.get("taglie", [])
                )
                self.items.append(item)

    def get_restaurant_name(self) -> str:
        """Ritorna nome del ristorante"""
        return self.raw_menu.get("ristorante", "Ristorante")

    def get_all_items(self) -> List[MenuItem]:
        """Ritorna tutti gli item del menu"""
        return self.items

    def get_sections(self) -> List[str]:
        """Ritorna lista delle sezioni"""
        return list(set(item.sezione for item in self.items))

    def get_items_by_section(self, section: str) -> List[MenuItem]:
        """Ritorna item di una sezione specifica"""
        return [item for item in self.items if item.sezione.lower() == section.lower()]

    def search(
        self,
        query: str = "",
        vegetariano: bool = False,
        vegano: bool = False,
        exclude_allergeni: List[int] = None,
        max_price: float = None,
        sezione: str = None
    ) -> List[MenuItem]:
        """Cerca nel menu con filtri"""
        results = self.items

        # Filtro per sezione
        if sezione:
            results = [i for i in results if i.sezione.lower() == sezione.lower()]

        # Filtro vegetariano
        if vegetariano:
            results = [i for i in results if i.vegetariano]

        # Filtro vegano
        if vegano:
            results = [i for i in results if i.vegano]

        # Filtro allergeni
        if exclude_allergeni:
            results = [i for i in results if not any(a in i.allergeni for a in exclude_allergeni)]

        # Filtro prezzo
        if max_price:
            results = [i for i in results if i.prezzo <= max_price]

        # Ricerca testuale
        if query:
            query_lower = query.lower()
            results = [
                i for i in results
                if query_lower in i.nome.lower() or query_lower in i.descrizione.lower()
            ]

        return results

    def find_by_name(self, name: str) -> Optional[MenuItem]:
        """Trova un item per nome (match esatto o parziale)"""
        name_lower = name.lower()

        # Match esatto
        for item in self.items:
            if item.nome.lower() == name_lower:
                return item

        # Match parziale
        for item in self.items:
            if name_lower in item.nome.lower() or item.nome.lower() in name_lower:
                return item

        return None

    def get_allergeni_description(self, allergeni_ids: List[int]) -> List[str]:
        """Converte ID allergeni in descrizioni"""
        return [
            self.allergeni_legend.get(str(a), f"Allergene {a}")
            for a in allergeni_ids
        ]

    def format_for_llm(self) -> str:
        """Formatta il menu per il contesto LLM"""
        text = f"MENU - {self.get_restaurant_name()}\n\n"

        current_section = ""
        for item in self.items:
            if item.sezione != current_section:
                current_section = item.sezione
                text += f"\n{current_section.upper()}:\n"

            # Formato item
            if item.taglie:
                sizes = " | ".join([f"{t['nome']}: €{t['prezzo']:.2f}" for t in item.taglie])
                text += f"- {item.nome}: {sizes}\n"
            elif item.prezzo:
                text += f"- {item.nome} (€{item.prezzo:.2f})"
            else:
                text += f"- {item.nome}"

            if item.descrizione:
                text += f": {item.descrizione}"

            tags = []
            if item.vegetariano:
                tags.append("VEGETARIANO")
            if item.vegano:
                tags.append("VEGANO")
            if tags:
                text += f" [{', '.join(tags)}]"

            if item.allergeni:
                allergen_names = self.get_allergeni_description(item.allergeni)
                text += f" | Allergeni: {', '.join(allergen_names)}"

            text += "\n"

        return text

    def format_section_for_display(self, section: str) -> str:
        """Formatta una sezione per visualizzazione"""
        items = self.get_items_by_section(section)
        if not items:
            return ""

        text = f"**{section}**\n"
        for item in items:
            if item.taglie:
                sizes = " | ".join([f"{t['nome']}: €{t['prezzo']:.2f}" for t in item.taglie])
                text += f"- {item.nome}: {sizes}\n"
            elif item.prezzo:
                text += f"- {item.nome} - €{item.prezzo:.2f}\n"
            else:
                text += f"- {item.nome}\n"

        return text
