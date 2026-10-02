"""
Catalogue d'accès de Kimia.

Règle : Voir ≠ agir ≠ administrer ≠ auditer.
  - `*` (CEO) donne tous les droits de LECTURE / ADMINISTRATION,
  - mais PAS les écritures sensibles de la caisse ni de la finance
    (WILDCARD_EXCLUDED) : elles doivent être accordées explicitement à un rôle
    (ex. CAISSIER, COMPTABLE).
Ainsi le CEO voit tous les mouvements sans pouvoir en créer ni en clôturer.
"""

# Écritures de caisse : jamais couvertes par le joker "*".
CASH_WRITE_PERMISSIONS: frozenset[str] = frozenset({
    "cash.create",
    "cash.cancel",
    "cash.close",
    "cash.reconcile",
})

# Permissions que le joker "*" ne couvre jamais : écritures de caisse et
# écritures de finance (revenus, paiements, rémunérations).
WILDCARD_EXCLUDED: frozenset[str] = CASH_WRITE_PERMISSIONS | {"finance.manage"}

# Catalogue : code -> (module, description). Sert à l'UI de gestion des rôles.
PERMISSION_CATALOG: dict[str, tuple[str, str]] = {
    # Caisse
    "cash.view": ("cash", "Voir les mouvements, soldes et clôtures de caisse"),
    "cash.create": ("cash", "Enregistrer une entrée/sortie de caisse"),
    "cash.cancel": ("cash", "Annuler un mouvement (écriture inverse motivée)"),
    "cash.close": ("cash", "Clôturer la caisse d'une journée"),
    "cash.reconcile": ("cash", "Rapprocher la caisse (comptage physique)"),
    "cash.audit": ("cash", "Consulter le journal d'audit de la caisse"),
    "cash.export": ("cash", "Exporter les rapports de caisse"),
    # Finance générale
    "finance.view": ("finance", "Voir revenus, paiements et rémunérations"),
    "finance.manage": ("finance", "Créer revenus, paiements et rémunérations (jamais couvert par le joker)"),
    # Sécurité / chat
    "security.view": ("security", "Voir événements de connexion, sessions et comptes verrouillés"),
    "security.manage": ("security", "Débloquer un compte, déconnecter une session"),
    "chat.manage": ("chat", "Voir tous les canaux projet et supprimer les messages d'autrui"),
    # Équipe / rôles
    "team.view": ("team", "Voir les membres"),
    "team.manage": ("team", "Gérer les membres"),
    "team.skills": ("team", "Gérer les compétences des membres"),
    "roles.manage": ("roles", "Créer des rôles et gérer leurs permissions"),
    # Développement
    "dev.view": ("dev", "Voir l'équipe et les projets de développement"),
    "dev.manage": ("dev", "Gérer l'équipe de développement"),
    "dev.tools.use": ("dev", "Utiliser les outils internes de développement"),
}

# Rôle « prêt à l'emploi » pour la personne chargée de la caisse.
CASHIER_ROLE = "CAISSIER"
CASHIER_PERMISSIONS: list[str] = [
    "dashboard.view",
    "notifications.view",
    "cash.view", "cash.create", "cash.cancel", "cash.close", "cash.export",
]


# Rôle « prêt à l'emploi » pour la tenue de la finance (écritures).
ACCOUNTANT_ROLE = "COMPTABLE"
ACCOUNTANT_PERMISSIONS: list[str] = [
    "dashboard.view",
    "notifications.view",
    "finance.view", "finance.manage",
]


def has_permission(codes: set[str] | list[str], required: str) -> bool:
    """Vrai si `required` est accordée, en tenant compte du joker restreint."""
    codes = set(codes)
    if required in codes:
        return True
    return "*" in codes and required not in WILDCARD_EXCLUDED


def effective_permissions(codes: set[str] | list[str]) -> list[str]:
    """Développe le joker : liste ce que l'utilisateur peut réellement faire."""
    codes = set(codes)
    if "*" in codes:
        known = set(PERMISSION_CATALOG) - WILDCARD_EXCLUDED
        return sorted((codes - {"*"}) | known | {"*"})
    return sorted(codes)


def holds_sensitive_write(codes: set[str] | list[str]) -> bool:
    """Vrai si le rôle accorde explicitement une écriture sensible (caisse / finance)."""
    return any(c in WILDCARD_EXCLUDED for c in codes)


def can_write_cash(codes: set[str] | list[str]) -> bool:
    return any(has_permission(codes, c) for c in CASH_WRITE_PERMISSIONS)
