"""
=============================================================================
 Analyse : "Qu'est-ce qui freine la croissance au Maroc ?"
=============================================================================
Ce script :
  1. Importe 3 séries trimestrielles publiées par le Haut Commissariat au
     Plan (HCP) - Comptes Nationaux Trimestriels :
        - Croissance économique (évolution du PIB en %, en glissement annuel)
        - Taux d'investissement / PIB (%)
        - Valeur ajoutée agricole (évolution en %, en glissement annuel)
  2. Nettoie et fusionne ces séries sur la colonne "Trimestre".
  3. Calcule quelques statistiques simples (corrélations, moyennes par
     période) qui permettent d'objectiver les facteurs qui freinent la
     croissance marocaine (dépendance à la pluviométrie, faiblesse relative
     de l'investissement, chocs conjoncturels).
  4. Génère un graphique PAR fichier (3 graphiques individuels), plus UN
     graphique combiné qui superpose les 3 séries.

Arborescence attendue (à respecter dans le dépôt GitHub) :

    projet_croissance/
    ├── data/
    │   ├── Croissance_economique_evolution_en_%.xlsx
    │   ├── Taux_d_investissement_PIB.xlsx
    │   └── Valeur_ajoutee_agricole_evolution_en_%.xlsx
    ├── analyse_croissance_maroc.py   <- ce script
    └── output/
        ├── graphique_croissance_pib.png          <- individuel
        ├── graphique_taux_investissement.png     <- individuel
        ├── graphique_valeur_ajoutee_agricole.png <- individuel
        └── graphique_croissance_maroc.png        <- combiné (les 3 séries)

Sources des données (HCP) :
  - https://www.hcp.ma/  (Comptes Nationaux Trimestriels, Haut Commissariat
    au Plan du Maroc)
=============================================================================
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

# -----------------------------------------------------------------------
# 0. Configuration des chemins
# -----------------------------------------------------------------------
DATA_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

FICHIER_CROISSANCE = os.path.join(
    DATA_DIR, "Croissance économique (évolution en %) - Tableau (3).xlsx"
)

FICHIER_INVESTISSEMENT = os.path.join(
    DATA_DIR, "Taux d'investissement_PIB - Tableau.xlsx"
)

FICHIER_AGRICULTURE = os.path.join(
    DATA_DIR, "Valeur ajoutée agricole (évolution en %) - Tableau.xlsx"
)

# -----------------------------------------------------------------------
# 1. Fonction générique de chargement/nettoyage d'un fichier HCP
# -----------------------------------------------------------------------
def charger_serie(chemin_fichier, nom_colonne_valeur):
    """
    Lit un fichier Excel exporté du site du HCP (format "Tableau"),
    supprime les lignes d'en-tête/source parasites et renvoie un
    DataFrame propre avec les colonnes : Trimestre, <nom_colonne_valeur>, Date.
    """
    df = pd.read_excel(chemin_fichier, sheet_name="Tableau", header=None)

    # Les données utiles sont dans les colonnes 1 (Trimestre) et 2 (valeur)
    df = df.iloc[:, [1, 2]]
    df.columns = ["Trimestre", nom_colonne_valeur]

    # On ne garde que les lignes où Trimestre a le format "AAAA:T"
    df = df[df["Trimestre"].astype(str).str.match(r"^\d{4}:\d$", na=False)]

    # Conversion de la valeur en numérique
    df[nom_colonne_valeur] = pd.to_numeric(df[nom_colonne_valeur], errors="coerce")
    df = df.dropna(subset=[nom_colonne_valeur]).reset_index(drop=True)

    df["Date"] = df["Trimestre"].apply(trimestre_vers_date)
    df = df.sort_values("Date").reset_index(drop=True)

    return df


def trimestre_vers_date(trimestre):
    """Convertit '2020:2' en une date approximative (milieu du trimestre)."""
    annee, trim = trimestre.split(":")
    mois = {"1": 2, "2": 5, "3": 8, "4": 11}[trim]
    return pd.Timestamp(year=int(annee), month=mois, day=15)


# -----------------------------------------------------------------------
# 2. Chargement des 3 séries + fusion pour l'analyse combinée
# -----------------------------------------------------------------------
def charger_donnees():
    croissance = charger_serie(FICHIER_CROISSANCE, "Croissance_PIB_%")
    investissement = charger_serie(FICHIER_INVESTISSEMENT, "Taux_investissement_PIB_%")
    agriculture = charger_serie(FICHIER_AGRICULTURE, "VA_agricole_%")

    # Fusion des 3 séries sur le trimestre (inner join = période commune)
    df = croissance[["Trimestre", "Croissance_PIB_%"]].merge(
        investissement[["Trimestre", "Taux_investissement_PIB_%"]], on="Trimestre", how="inner"
    )
    df = df.merge(
        agriculture[["Trimestre", "VA_agricole_%"]], on="Trimestre", how="inner"
    )

    df["Date"] = df["Trimestre"].apply(trimestre_vers_date)
    df = df.sort_values("Date").reset_index(drop=True)
    df["Annee"] = df["Date"].dt.year

    return croissance, investissement, agriculture, df


# -----------------------------------------------------------------------
# 3. Analyse chiffrée
# -----------------------------------------------------------------------
def analyser(df):
    print("=" * 70)
    print("APERÇU DES DONNÉES FUSIONNÉES")
    print("=" * 70)
    print(df[["Trimestre", "Croissance_PIB_%", "Taux_investissement_PIB_%",
               "VA_agricole_%"]].to_string(index=False))

    print("\n" + "=" * 70)
    print("STATISTIQUES DESCRIPTIVES (période disponible : "
          f"{df['Trimestre'].iloc[0]} à {df['Trimestre'].iloc[-1]})")
    print("=" * 70)
    print(df[["Croissance_PIB_%", "Taux_investissement_PIB_%",
               "VA_agricole_%"]].describe().round(2))

    # Corrélations : quel facteur "bouge" le plus avec la croissance ?
    corr_agri = df["Croissance_PIB_%"].corr(df["VA_agricole_%"])
    corr_invest = df["Croissance_PIB_%"].corr(df["Taux_investissement_PIB_%"])

    print("\n" + "=" * 70)
    print("CORRÉLATIONS AVEC LA CROISSANCE DU PIB")
    print("=" * 70)
    print(f"Croissance PIB vs Valeur ajoutée agricole      : r = {corr_agri:.2f}")
    print(f"Croissance PIB vs Taux d'investissement/PIB    : r = {corr_invest:.2f}")

    # Repérage des trimestres de croissance la plus faible / négative
    pires_trimestres = df.nsmallest(5, "Croissance_PIB_%")[
        ["Trimestre", "Croissance_PIB_%", "VA_agricole_%", "Taux_investissement_PIB_%"]
    ]
    print("\n" + "=" * 70)
    print("LES 5 TRIMESTRES DE CROISSANCE LA PLUS FAIBLE")
    print("=" * 70)
    print(pires_trimestres.to_string(index=False))

    # Moyenne de croissance par année (pour lisser les à-coups trimestriels)
    moyenne_annuelle = df.groupby("Annee")["Croissance_PIB_%"].mean().round(2)
    print("\n" + "=" * 70)
    print("CROISSANCE MOYENNE ANNUELLE (%)")
    print("=" * 70)
    print(moyenne_annuelle.to_string())

    return {
        "corr_agri": corr_agri,
        "corr_invest": corr_invest,
        "pires_trimestres": pires_trimestres,
        "moyenne_annuelle": moyenne_annuelle,
    }


# -----------------------------------------------------------------------
# 4a. Graphique individuel générique (un fichier = un graphe)
# -----------------------------------------------------------------------
def tracer_graphique_individuel(df, colonne, titre, couleur, chemin_sortie):
    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(df["Date"], df[colonne], color=couleur, linewidth=2,
            marker="o", markersize=3)
    ax.axhline(0, color="grey", linewidth=0.8)
    ax.set_xlabel("Trimestre")
    ax.set_ylabel(colonne.replace("_", " "))
    ax.set_title(titre, fontsize=12, fontweight="bold")
    ax.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(chemin_sortie, dpi=200)
    plt.close(fig)
    print(f"Graphique enregistré : {chemin_sortie}")


# -----------------------------------------------------------------------
# 4b. Graphique combiné (les 3 séries superposées)
# -----------------------------------------------------------------------
def tracer_graphique_combine(df, chemin_sortie):
    fig, ax1 = plt.subplots(figsize=(13, 6))

    # Axe 1 : croissance du PIB et VA agricole (%, échelle commune)
    ax1.plot(df["Date"], df["Croissance_PIB_%"], color="#1f77b4",
              linewidth=2, marker="o", markersize=3, label="Croissance du PIB (%)")
    ax1.plot(df["Date"], df["VA_agricole_%"], color="#2ca02c",
              linewidth=1.5, linestyle="--", alpha=0.8,
              label="Valeur ajoutée agricole (%)")
    ax1.axhline(0, color="grey", linewidth=0.8)
    ax1.set_xlabel("Trimestre")
    ax1.set_ylabel("Évolution en % (glissement annuel)")

    # Axe 2 : taux d'investissement / PIB (échelle différente, à droite)
    ax2 = ax1.twinx()
    ax2.plot(df["Date"], df["Taux_investissement_PIB_%"], color="#d62728",
              linewidth=2, label="Taux d'investissement / PIB (%)")
    ax2.set_ylabel("Taux d'investissement / PIB (%)")

    # Légende combinée des deux axes
    lignes_1, labels_1 = ax1.get_legend_handles_labels()
    lignes_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(lignes_1 + lignes_2, labels_1 + labels_2, loc="upper left", fontsize=9)

    plt.title("Maroc — Croissance du PIB, valeur ajoutée agricole et taux "
              "d'investissement\n(données trimestrielles, source : HCP)",
              fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(chemin_sortie, dpi=200)
    plt.close(fig)
    print(f"Graphique enregistré : {chemin_sortie}")


# -----------------------------------------------------------------------
# 5. Programme principal
# -----------------------------------------------------------------------
def main():
    croissance, investissement, agriculture, df = charger_donnees()
    analyser(df)

    # --- Un graphique par fichier / par série ---
    tracer_graphique_individuel(
        croissance, "Croissance_PIB_%",
        "Maroc — Croissance économique (évolution en %)",
        "#1f77b4",
        os.path.join(OUTPUT_DIR, "graphique_croissance_pib.png"),
    )
    tracer_graphique_individuel(
        investissement, "Taux_investissement_PIB_%",
        "Maroc — Taux d'investissement / PIB (%)",
        "#d62728",
        os.path.join(OUTPUT_DIR, "graphique_taux_investissement.png"),
    )
    tracer_graphique_individuel(
        agriculture, "VA_agricole_%",
        "Maroc — Valeur ajoutée agricole (évolution en %)",
        "#2ca02c",
        os.path.join(OUTPUT_DIR, "graphique_valeur_ajoutee_agricole.png"),
    )

    # --- Graphique combiné (les 3 séries superposées) ---
    tracer_graphique_combine(
        df, os.path.join(OUTPUT_DIR, "graphique_croissance_maroc.png")
    )


if __name__ == "__main__":
    main()