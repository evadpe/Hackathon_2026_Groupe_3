"""
Generation et affichage du rapport de verification.
Utilise la bibliotheque Rich pour un rendu terminal colore.
"""

import sys
from models import RapportVerification, NiveauAlerte

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# Force UTF-8 pour les terminaux Windows
console = Console(highlight=False, legacy_windows=False)

_COULEUR_NIVEAU = {
    "ERREUR":        "bold red",
    "AVERTISSEMENT": "bold yellow",
    "INFO":          "cyan",
}
_LABEL_NIVEAU = {
    "ERREUR":        "[ERREUR]",
    "AVERTISSEMENT": "[AVERT.]",
    "INFO":          "[INFO]  ",
}
_COULEUR_STATUT = {
    "NON_CONFORME": "bold red",
    "A_VERIFIER":   "bold yellow",
    "CONFORME":     "bold green",
}
_LABEL_STATUT = {
    "NON_CONFORME": "[X] NON CONFORME",
    "A_VERIFIER":   "[!] A VERIFIER",
    "CONFORME":     "[OK] CONFORME",
}


def afficher_rapport(rapport: RapportVerification) -> None:
    """Affiche le rapport complet dans le terminal avec couleurs et tableaux."""

    console.print()

    statut_couleur = _COULEUR_STATUT.get(rapport.statut, "white")
    label_statut   = _LABEL_STATUT.get(rapport.statut, rapport.statut)

    # En-tete
    console.print(Panel(
        f"[bold]StepAhead Industries[/bold] - Rapprochement tripartite\n\n"
        f"  BC      : [cyan]{rapport.numero_bon_commande}[/cyan]\n"
        f"  Devis   : [cyan]{rapport.numero_devis or 'N/A (non fourni)'}[/cyan]\n"
        f"  Facture : [cyan]{rapport.numero_facture}[/cyan]\n"
        f"  Date    : {rapport.date_verification[:10]}\n\n"
        f"  Statut  : [{statut_couleur}]{label_statut}[/{statut_couleur}]\n\n"
        f"  [red]Erreurs : {rapport.nb_erreurs}[/red]   "
        f"[yellow]Avertissements : {rapport.nb_avertissements}[/yellow]   "
        f"[cyan]Infos : {rapport.nb_infos}[/cyan]",
        title=f"[{statut_couleur}]RAPPORT DE VERIFICATION[/{statut_couleur}]",
        border_style=statut_couleur.replace("bold ", ""),
    ))

    if not rapport.alertes:
        console.print(
            "\n[bold green]Aucune anomalie detectee - Documents conformes.[/bold green]\n"
        )
        return

    # Tableau des alertes
    table = Table(
        title="Detail des anomalies detectees",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold white on dark_blue",
        show_lines=True,
    )
    table.add_column("Niveau",    style="bold", width=12, justify="center")
    table.add_column("Categorie", width=16)
    table.add_column("Reference", width=16)
    table.add_column("Message",   width=50)
    table.add_column("Attendu",   width=24)
    table.add_column("Recu",      width=24)
    table.add_column("Ecart",     width=22)

    for alerte in rapport.alertes:
        niv = alerte.niveau.value
        col = _COULEUR_NIVEAU.get(niv, "white")
        lbl = _LABEL_NIVEAU.get(niv, niv)
        table.add_row(
            f"[{col}]{lbl}[/{col}]",
            alerte.categorie,
            alerte.reference_ligne or "-",
            alerte.message,
            alerte.valeur_attendue or "-",
            alerte.valeur_recue    or "-",
            f"[{col}]{alerte.ecart or '-'}[/{col}]",
        )

    console.print(table)
    console.print()

    # Analyse semantique
    if rapport.analyse_semantique:
        console.print(Panel(
            rapport.analyse_semantique,
            title="[bold blue]Analyse semantique (regles metier)[/bold blue]",
            border_style="blue",
        ))
        console.print()


def exporter_rapport_json(rapport: RapportVerification) -> str:
    """Serialise le rapport en JSON indente."""
    return rapport.model_dump_json(indent=2, exclude_none=False)
