"""Génération des abaques de portées admissibles (matplotlib)."""
from __future__ import annotations

import tomllib
from pathlib import Path

import pandas as pd
from loguru import logger


# Portées affichées en colonnes (mm)
_PORTEES_MM = [0,500,1000,1500,2000, 2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000, 6500, 7000, 7500, 8000, 8500, 9000, 9500, 10000]

_CHARTE_PAR_DEFAUT = Path(__file__).parent / "charte_graphique.toml"


def _lire_charte(charte: Path | None) -> dict:
    """Charge la charte graphique TOML (fichier par défaut si non fourni)."""
    chemin = charte if charte and charte.exists() else _CHARTE_PAR_DEFAUT
    with open(chemin, "rb") as f:
        return tomllib.load(f)


def generer_graphiques(
    donnees: Path,
    configs_calcul: Path,
    sortie: Path,
    fmt: str,
    charte: Path | None = None,
) -> None:
    """Charge les données et génère un abaque par groupe (type_poutre + usage)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    cg = _lire_charte(charte)

    try:
        df = pd.read_csv(donnees, sep=";")
    except Exception as e:
        logger.error(f"Impossible de lire {donnees} : {e}")
        return

    # Entraxes depuis configs_calcul.toml
    entraxe_fn = _lire_entraxes(configs_calcul)

    # Garder uniquement les lignes admissibles
    df = df[df["statut"] == "admis"].copy()
    if df.empty:
        logger.warning("Aucun résultat admissible dans le fichier.")
        return

    # Ajouter entraxe_mm depuis la fonction de résolution
    df["entraxe_mm"] = df["id_config_calcul"].map(entraxe_fn)

    # Portée max admissible par (config, produit)
    idx_max = df.groupby(["id_config_calcul", "id_produit"])["longueur_m"].idxmax()
    df_max = df.loc[idx_max].copy()
    df_max["L_max_mm"] = (df_max["longueur_m"] * 1000).round(0).astype(int)

    # Dédoublonnage : même produit + même entraxe + même usage → garder la portée max
    df_max = (
        df_max
        .sort_values("L_max_mm", ascending=False)
        .drop_duplicates(subset=["id_produit", "b_mm", "h_mm", "classe_resistance",
                                  "entraxe_mm", "type_poutre", "usage"])
        .reset_index(drop=True)
    )

    # Indice économique : section / (entraxe × portée) — normalisé sur le groupe
    df_max["indice_brut"] = (df_max["b_mm"] * df_max["h_mm"]) / (
        df_max["entraxe_mm"] * df_max["L_max_mm"]
    )

    # Palette de couleurs par entraxe (depuis charte graphique, sur tous les groupes)
    entraxes_uniques = sorted(df_max["entraxe_mm"].dropna().unique())
    palette = cg.get("couleurs", {}).get("entraxes", {}).get("couleurs", [
        "#2196f3", "#4caf50", "#ff9800", "#e91e63", "#9c27b0", "#00bcd4"
    ])
    couleur_entraxe = {e: palette[i % len(palette)] for i, e in enumerate(entraxes_uniques)}

    # Grouper par (type_poutre, usage) → une figure par groupe
    sortie.mkdir(parents=True, exist_ok=True)
    sous_dossier = sortie / "par_config"
    sous_dossier.mkdir(exist_ok=True)

    groupes = df_max.groupby(["type_poutre", "usage"])
    pdf_global = sortie / "tous_les_abaques.pdf"

    with PdfPages(pdf_global) as pdf:
        for (type_poutre, usage), df_groupe in groupes:
            nom = f"{type_poutre}_{usage}"
            logger.info(f"Génération : {nom}")
            fig = _generer_figure(df_groupe, type_poutre, usage, couleur_entraxe, cg)
            # Fichier individuel
            chemin_ind = sous_dossier / f"{nom}.{fmt}"
            fig.savefig(chemin_ind, dpi=150, bbox_inches="tight")
            # Page dans le PDF global
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

    logger.info(f"PDF global : {pdf_global}")
    logger.info(f"Fichiers individuels : {sous_dossier}")


def _lire_entraxes(configs_calcul: Path) -> dict[str, float]:
    """Retourne une fonction id_config_calcul → entraxe_mm.

    Stratégie :
    1. Suffixe '_E{valeur}' dans l'ID (configs expansées, ex: SOLIVE_HAB_600_E0.6)
    2. Valeur scalaire dans configs_calcul.toml (configs non expansées)
    """
    import re

    # Lecture TOML pour les configs scalaires
    toml_entraxes: dict[str, float] = {}
    if configs_calcul.exists():
        with open(configs_calcul, "rb") as f:
            data = tomllib.load(f)
        for cfg in data.get("config_calcul", []):
            valeur = cfg.get("entraxe_m", 0.6)
            if isinstance(valeur, (int, float)):
                toml_entraxes[cfg["id_config_calcul"]] = float(valeur) * 1000

    def entraxe_depuis_id(id_config: str) -> float:
        # Suffixe _E{valeur} généré par l'expansion cartésienne
        m = re.search(r"_E([\d.]+)$", id_config)
        if m:
            return float(m.group(1)) * 1000
        # Fallback : TOML scalaire
        if id_config in toml_entraxes:
            return toml_entraxes[id_config]
        return 600.0  # repli

    return entraxe_depuis_id


def _generer_figure(df: pd.DataFrame, type_poutre: str, usage: str, couleur_entraxe: dict, cg: dict):
    """Génère la figure matplotlib pour un groupe (type_poutre, usage).

    Architecture : un seul axes couvre la zone des barres (x = portée mm, y = rang de ligne,
    axe y inversé). Les colonnes texte (code, produit, entraxe, indice) utilisent un transform
    mixte via blended_transform_factory (x en fraction de figure, y en coordonnées données)
    — alignement vertical garanti sans calcul manuel.
    Les barres sont tracées avec ax.barh : chaque barre est confinée dans son rang.
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.transforms import blended_transform_factory

    # Normaliser l'indice dans le groupe (min → 1.00)
    indice_min = df["indice_brut"].min()
    df = df.copy()
    df["indice"] = (df["indice_brut"] / indice_min).round(2)

    # Trier par section (b×h) puis entraxe
    df = df.sort_values(["b_mm", "h_mm", "classe_resistance", "entraxe_mm"])

    lignes = _construire_lignes(df)
    n_lignes = len(lignes)
    if n_lignes == 0:
        return plt.figure()

    # Paramètres charte graphique
    fig_cg = cg.get("figure", {})
    pol = cg.get("polices", {})
    coul_fond = cg.get("couleurs", {}).get("fond", {})
    coul_txt = cg.get("couleurs", {}).get("texte", {})
    coul_sep = cg.get("couleurs", {}).get("separateurs", {})
    coul_gri = cg.get("couleurs", {}).get("grille", {})

    largeur = fig_cg.get("largeur", 16)
    h_par_ligne = fig_cg.get("hauteur_par_ligne", 0.45)

    # Hauteurs fixes en pouces pour chaque zone
    H_TITRE   = 0.50   # titre
    H_ENTETE  = 0.45   # en-têtes colonnes + labels portées
    H_LEGENDE = 0.40   # légende entraxes
    H_BARRES_MIN = n_lignes * h_par_ligne

    # L'espace extra (hauteur_min) s'absorbe dans les barres → pas de blanc parasite
    hauteur = max(fig_cg.get("hauteur_min", 2.5), H_TITRE + H_ENTETE + H_BARRES_MIN + H_LEGENDE)
    H_BARRES = hauteur - H_TITRE - H_ENTETE - H_LEGENDE

    # Positions axes (calculées depuis les hauteurs absolues → titre/en-têtes toujours juste au-dessus)
    AX_B = H_LEGENDE / hauteur
    AX_T = (H_LEGENDE + H_BARRES) / hauteur

    portee_min = _PORTEES_MM[0]
    portee_max = _PORTEES_MM[-1]

    # ----- Layout horizontal (fractions de figure) -----
    # [0.01 – 0.06] code SAPEG
    # [0.06 – 0.22] produit (b×h classe)
    # [0.22 – 0.26] entraxe mm
    # [AX_L – AX_R] axes barres
    # [AX_R – 0.99] indice
    AX_L = 0.26   # bord gauche de l'axes barres
    AX_R = 0.91   # bord droit

    fig = plt.figure(figsize=(largeur, hauteur))
    ax = fig.add_axes([AX_L, AX_B, AX_R - AX_L, AX_T - AX_B])

    # Coordonnées données : x = portée mm, y = rang (0 = 1ère ligne en haut)
    ax.set_xlim(portee_min, portee_max)
    ax.set_ylim(n_lignes - 0.5, -0.5)   # inversé : rang 0 en haut

    # Supprimer ticks et spines
    ax.set_xticks([])
    ax.set_yticks([])
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Transform mixte : x en fraction de figure [0,1], y en coordonnées données de l'axes
    trans_mix = blended_transform_factory(fig.transFigure, ax.transData)

    # ----- Grille verticale des portées -----
    for p_mm in _PORTEES_MM:
        ax.axvline(p_mm, color=coul_gri.get("verticale", "#cccccc"), lw=0.5, ls="--", zorder=0)

    # ----- Groupes produit : fond + cellules fusionnées -----
    groupes_produit: list[tuple[int, int]] = []
    i_debut = 0
    for i, ligne in enumerate(lignes):
        produit_i = (ligne["id_produit"], ligne["b_mm"], ligne["h_mm"], ligne["classe_resistance"])
        produit_suivant = (
            (lignes[i + 1]["id_produit"], lignes[i + 1]["b_mm"],
             lignes[i + 1]["h_mm"], lignes[i + 1]["classe_resistance"])
            if i + 1 < n_lignes else None
        )
        if produit_i != produit_suivant:
            groupes_produit.append((i_debut, i))
            i_debut = i + 1

    for g_idx, (i_d, i_f) in enumerate(groupes_produit):
        couleur_fond_g = coul_fond.get("pair", "#f0f0f0") if g_idx % 2 == 0 else coul_fond.get("impair", "#ffffff")

        # Fond dans la zone barres
        ax.axhspan(i_d - 0.5, i_f + 0.5, facecolor=couleur_fond_g, alpha=0.5, zorder=0)

        # Séparateur fort entre groupes (étendu aux colonnes texte via trans_mix)
        if g_idx > 0:
            ax.axhline(i_d - 0.5, color=coul_sep.get("fort", "#aaaaaa"), lw=0.8, zorder=1)
            ax.plot(
                [0.01, AX_L], [i_d - 0.5, i_d - 0.5],
                color=coul_sep.get("fort", "#aaaaaa"), lw=0.8, zorder=1,
                transform=trans_mix, clip_on=False,
            )

        # Texte fusionné : centré verticalement sur le groupe
        y_centre = (i_d + i_f) / 2
        ligne_ref = lignes[i_d]
        code = str(ligne_ref["id_produit"])
        produit = f"{int(ligne_ref['b_mm'])}×{int(ligne_ref['h_mm'])} {ligne_ref['classe_resistance']}"
        fs_prod = pol.get("produit", 7)
        c_prod = coul_txt.get("produit", "#000000")

        ax.text(0.035, y_centre, code, transform=trans_mix,
                ha="center", va="center", fontsize=fs_prod, color=c_prod, clip_on=False)
        ax.text(0.14, y_centre, produit, transform=trans_mix,
                ha="center", va="center", fontsize=fs_prod, color=c_prod, clip_on=False)

    # ----- Sous-lignes (une par entraxe) -----
    for i, ligne in enumerate(lignes):
        y_pos = i   # coordonnée donnée = rang
        entraxe = ligne["entraxe_mm"]
        L_max = ligne["L_max_mm"]
        couleur_barre = couleur_entraxe.get(entraxe, "#4caf50")

        # Texte entraxe (à gauche de l'axes)
        ax.text(0.24, y_pos, str(int(entraxe)), transform=trans_mix,
                ha="center", va="center",
                fontsize=pol.get("entraxe", 7), color=coul_txt.get("produit", "#000000"),
                clip_on=False)

        # Texte indice (à droite de l'axes)
        ax.text(0.945, y_pos, f"{ligne['indice']:.2f}", transform=trans_mix,
                ha="center", va="center",
                fontsize=pol.get("indice", 8), fontweight="bold",
                color=coul_txt.get("produit", "#000000"), clip_on=False)

        # Barre horizontale — ax.barh garantit que chaque barre reste dans son rang
        L_max_affiche = min(L_max, portee_max)
        ax.barh(y_pos, L_max_affiche - portee_min, height=0.65,
                left=portee_min, color=couleur_barre, zorder=2, linewidth=0)

        # Valeur portée max (indicateur ▶ si hors tableau)
        label_val = f"▶ {L_max}" if L_max > portee_max else str(L_max)
        ax.text(
            L_max_affiche + (portee_max - portee_min) * 0.004, y_pos,
            label_val, ha="left", va="center",
            fontsize=pol.get("valeur_bar", 6.5), color=coul_txt.get("valeur_bar", "#1a1a1a"),
            fontweight="bold", zorder=3, clip_on=False,
        )

        # Séparateur léger entre sous-lignes d'un même groupe (sauf la dernière)
        for (i_d, i_f) in groupes_produit:
            if i_d <= i < i_f:
                ax.axhline(i + 0.5, color=coul_sep.get("leger", "#dddddd"), lw=0.4, zorder=1)
                ax.plot(
                    [0.22, AX_L], [i + 0.5, i + 0.5],
                    color=coul_sep.get("leger", "#dddddd"), lw=0.4, zorder=1,
                    transform=trans_mix, clip_on=False,
                )
                break

    # ----- En-têtes colonnes (au-dessus de l'axes, en coordonnées figure) -----
    y_entetes = AX_T + 0.005
    fs_e = pol.get("entete", 7)
    c_e = coul_txt.get("entete", "#000000")

    fig.text(0.035, y_entetes, "Code\nSAPEG",
             ha="center", va="bottom", fontsize=fs_e, fontweight="bold", color=c_e)
    fig.text(0.14, y_entetes, "Produit\n(b×h classe)",
             ha="center", va="bottom", fontsize=fs_e, fontweight="bold", color=c_e)
    fig.text(0.24, y_entetes, "Entraxe\nmm",
             ha="center", va="bottom", fontsize=fs_e, fontweight="bold", color=c_e)
    fig.text((AX_L + AX_R) / 2, y_entetes + 0.03, "Portée admissible en mm",
             ha="center", va="bottom", fontsize=8, fontweight="bold")
    fig.text(0.945, y_entetes, "Indice",
             ha="center", va="bottom", fontsize=fs_e, fontweight="bold", color=c_e)

    # Labels des portées (juste au-dessus de l'axes)
    for p_mm in _PORTEES_MM:
        x_fig = AX_L + (p_mm - portee_min) / (portee_max - portee_min) * (AX_R - AX_L)
        fig.text(x_fig, y_entetes, str(p_mm),
                 ha="center", va="bottom", fontsize=6, color="#444444")

    # Ligne séparatrice en-tête
    fig.add_artist(plt.Line2D(
        [0.01, 0.99], [AX_T, AX_T],
        color=coul_sep.get("entete", "#333333"), linewidth=1.0,
        transform=fig.transFigure, clip_on=False,
    ))

    # ----- Titre -----
    titre = f"{type_poutre.upper()}  —  {usage.replace('_', ' ')}"
    fig.text(0.01, 0.97, titre,
             fontsize=pol.get("titre", 13), fontweight="bold", va="top",
             color=coul_txt.get("titre", "#000000"))

    # ----- Légende entraxes -----
    legendes = [
        mpatches.Patch(facecolor=c, label=f"Entraxe {int(e)} mm")
        for e, c in couleur_entraxe.items()
    ]
    ax.legend(
        handles=legendes,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=min(len(legendes), 6),
        fontsize=7,
        frameon=False,
    )

    fig.patch.set_facecolor("white")
    return fig


def _construire_lignes(df: pd.DataFrame) -> list[dict]:
    """Convertit le DataFrame en liste de dicts pour l'affichage."""
    lignes = []
    for _, row in df.iterrows():
        lignes.append({
            "id_produit": row["id_produit"],
            "b_mm": row["b_mm"],
            "h_mm": row["h_mm"],
            "classe_resistance": row["classe_resistance"],
            "entraxe_mm": row.get("entraxe_mm", 600),
            "L_max_mm": row["L_max_mm"],
            "indice": row["indice"],
            "classe_service": row.get("classe_service", 1),
        })
    return lignes
