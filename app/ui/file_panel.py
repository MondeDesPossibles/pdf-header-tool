# ==============================================================================
# app/ui/file_panel.py — File list panel mixin
# [CODEX] Step 4.7.6: methods extracted from PDFHeaderApp
# ==============================================================================

import customtkinter as ctk

from app.constants import COLORS


class FilePanelMixin:
    def _build_file_panel(self, parent):
        """Construit le panneau scrollable à droite listant les fichiers PDF chargés."""
        ctk.CTkLabel(parent, text="FICHIERS",
                     fg_color="transparent", text_color=COLORS["text_placeholder"],
                     font=("Segoe UI", 10, "bold"),
                     anchor="w").pack(anchor="w", padx=10, pady=(10, 4))
        ctk.CTkFrame(parent, fg_color=COLORS["input_border"], height=1,
                     corner_radius=0).pack(fill="x", padx=10)

        self.file_cards_scroll = ctk.CTkScrollableFrame(
            parent, fg_color=COLORS["bg_file_panel"], corner_radius=0
        )
        self.file_cards_scroll.pack(fill="both", expand=True)

        self.file_card_frames = {}
        self.file_card_badges = {}

        self.lbl_file_counter = ctk.CTkLabel(
            parent, text="0 / 0 fichiers traités",
            fg_color=COLORS["bg_topbar"], text_color=COLORS["text_placeholder"],
            font=("Segoe UI", 11)
        )
        self.lbl_file_counter.pack(fill="x", pady=4)

    def _populate_file_panel(self):
        """Peuple le panneau fichiers avec une carte par PDF (état initial : non_traite)."""
        for frame in self.file_card_frames.values():
            frame.destroy()
        self.file_card_frames = {}
        self.file_card_badges = {}
        for i, path in enumerate(self.pdf_files):
            self._create_file_card(i, path)
        self._refresh_file_counter()

    def _create_file_card(self, idx, path):
        """Crée le widget carte pour un fichier (nom tronqué + badge état coloré).
        Retourne le frame de la carte (stocké dans self._file_cards[idx]).
        """
        frame = ctk.CTkFrame(self.file_cards_scroll,
                             fg_color=COLORS["input_bg"], corner_radius=6)
        frame.pack(fill="x", padx=6, pady=3)
        frame.bind("<Button-1>", lambda e, i=idx: self._jump_to_file(i))

        name_lbl = ctk.CTkLabel(frame, text=path.stem,
                                 fg_color="transparent", text_color=COLORS["text_primary"],
                                 font=("Segoe UI", 12), anchor="w",
                                 wraplength=180)
        name_lbl.pack(anchor="w", padx=8, pady=(6, 0))
        name_lbl.bind("<Button-1>", lambda e, i=idx: self._jump_to_file(i))

        badge_lbl = ctk.CTkLabel(frame, text="",
                                  fg_color="transparent", text_color=COLORS["text_tertiary"],
                                  font=("Segoe UI", 10), anchor="w")
        badge_lbl.pack(anchor="w", padx=8, pady=(0, 6))
        badge_lbl.bind("<Button-1>", lambda e, i=idx: self._jump_to_file(i))

        self.file_card_frames[idx] = frame
        self.file_card_badges[idx] = badge_lbl

    def _refresh_card(self, idx):
        """Met à jour la couleur de fond et le texte du badge d'une carte selon son état.
        États : non_traite (neutre), traite (vert), passe (gris), erreur (rouge).
        """
        if idx not in self.file_card_frames:
            return
        frame = self.file_card_frames[idx]
        badge = self.file_card_badges[idx]
        state = self.file_states.get(idx, "non_traite")

        if idx == self.idx:
            frame.configure(fg_color=COLORS["card_active_bg"])
            badge.configure(text="▶ En cours", text_color=COLORS["accent_blue"])
        elif state == "traite":
            frame.configure(fg_color=COLORS["card_done_bg"])
            badge.configure(text="✓ Modifié", text_color=COLORS["accent_green"])
        elif state == "passe":
            frame.configure(fg_color=COLORS["card_passe_bg"])
            badge.configure(text="→ Ignoré", text_color=COLORS["text_unit"])
        elif state == "erreur":
            frame.configure(fg_color=COLORS["card_error_bg"])
            badge.configure(text="⚠ Erreur", text_color=COLORS["error_red"])
        else:
            frame.configure(fg_color=COLORS["input_bg"])
            badge.configure(text="", text_color=COLORS["text_tertiary"])

    def _refresh_all_cards(self):
        """Rafraîchit toutes les cartes du panneau fichiers."""
        for i in range(len(self.pdf_files)):
            self._refresh_card(i)
        self._refresh_file_counter()

    def _refresh_file_counter(self):
        """Met à jour le compteur 'X / Y fichiers traités' en bas du panneau."""
        done = sum(1 for s in self.file_states.values() if s in ("traite", "passe"))
        total = len(self.pdf_files)
        self.lbl_file_counter.configure(text=f"{done} / {total} fichiers traités")

