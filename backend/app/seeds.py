"""
Seed initial — à exécuter après un reset :
    python -m app.seeds

Structure : Service → Catégories → Prestations.
29 prestations réparties en 6 catégories.
Chaque prestation a ses champs de formulaire et ses templates d'activités.

Idempotent : relancer le script ne duplique rien.
"""

from app.database import SessionLocal
from app.models import (
    # auth
    Permission, Role, RolePermission, Skill,
    Position, PositionSkill,
    # business
    Category, EventType, FormField, Service, ServiceEventType, ServiceFormField,
    # chat
    Channel, ChannelType,
    # content
    Platform,
    # workflow
    ActivityPriority, ActivityTemplate, ChecklistTemplateItem,
)


# --------------------------------------------------------------------------- #
# Rôles et permissions
# --------------------------------------------------------------------------- #
ROLES = ["CEO", "DA", "CM"]

PERMISSIONS_BY_ROLE = {
    "CEO": ["*"],
    "DA": [
        "dashboard.view",
        "requests.view", "requests.manage",
        "clients.view", "clients.manage",
        "projects.view", "projects.manage",
        "activities.view", "activities.manage", "activities.assign",
        "planning.view", "planning.manage",
        "publications.view", "publications.create", "publications.validate",
        "portfolio.view", "portfolio.manage",
        "services.view", "services.manage",
        "team.view", "team.skills",
        "documents.view", "documents.upload", "documents.delete",
        "notifications.view",
    ],
    "CM": [
        "dashboard.view",
        "projects.view_assigned",
        "activities.view_assigned", "activities.complete",
        "planning.view_own",
        "publications.view", "publications.create", "publications.submit",
        "documents.view", "documents.upload",
        "notifications.view",
    ],
}


# --------------------------------------------------------------------------- #
# Catalogue — 6 catégories
# --------------------------------------------------------------------------- #
CATEGORIES = [
    "Photographie",
    "Vidéo",
    "Conception graphique",
    "Développement web",
    "Communication digitale",
    "Invitations digitales",
]

EVENT_TYPES = ["Mariage", "Anniversaire", "Conférence", "Baptême", "Autre"]

PLATFORMS = ["Instagram", "Facebook", "TikTok", "LinkedIn"]


# --------------------------------------------------------------------------- #
# Compétences
# --------------------------------------------------------------------------- #
SKILLS = [
    "Photography",
    "Video",
    "Video Editing",
    "Graphic Design",
    "Art Direction",
    "Web Development",
    "Mobile Development",
    "UI/UX Design",
    "Community Management",
    "Digital Advertising",
    "Copywriting",
    "Writing",
    "Storytelling",
    "Sound Design",
    "Motion Design",
    "Color Grading",
    "SEO",
]


# --------------------------------------------------------------------------- #
# Postes (métiers)
# --------------------------------------------------------------------------- #
POSITIONS = [
    {"name": "Développeur web", "description": "Développement de sites web.",
     "skills": ["Web Development", "UI/UX Design"], "order": 1},
    {"name": "Développeur mobile", "description": "Développement d'applications mobiles.",
     "skills": ["Mobile Development", "UI/UX Design"], "order": 2},
    {"name": "Scénariste", "description": "Écriture de scénarios et concepts.",
     "skills": ["Writing", "Storytelling", "Art Direction"], "order": 3},
    {"name": "Vidéaste", "description": "Tournage et captation vidéo.",
     "skills": ["Video", "Art Direction"], "order": 4},
    {"name": "Monteur", "description": "Montage et post-production vidéo.",
     "skills": ["Video Editing", "Color Grading", "Sound Design", "Motion Design"], "order": 5},
    {"name": "Graphiste", "description": "Création graphique et identité visuelle.",
     "skills": ["Graphic Design", "Art Direction", "UI/UX Design"], "order": 6},
    {"name": "Photographe", "description": "Prise de vue et retouche photo.",
     "skills": ["Photography", "Art Direction"], "order": 7},
    {"name": "Community manager", "description": "Gestion des réseaux sociaux.",
     "skills": ["Community Management", "Digital Advertising", "Copywriting"], "order": 8},
]


# --------------------------------------------------------------------------- #
# Champs de formulaire communs (présents dans TOUTES les prestations)
# --------------------------------------------------------------------------- #
COMMON_FORM_FIELDS = [
    ("Nom complet",       "text",     None, True),
    ("Email",             "email",    None, True),
    ("Téléphone",         "tel",      None, True),
    ("Lieu",              "text",     None, False),
    ("Détails du projet", "textarea", None, False),
]


# --------------------------------------------------------------------------- #
# Prestations : (catégorie, nom, description, prix|None, [types d'événements])
# --------------------------------------------------------------------------- #
SERVICES = [
    # === 1. PHOTOGRAPHIE ===
    ("Photographie", "Photographie événementielle",
     "Couverture photo complète d'un événement (conférence, gala, cérémonie).",
     150000, ["Conférence", "Autre"]),
    ("Photographie", "Mariage",
     "Reportage photo complet du mariage, des préparatifs à la soirée.",
     250000, ["Mariage"]),
    ("Photographie", "Anniversaire",
     "Couverture photo d'anniversaire (enfant, adulte).",
     100000, ["Anniversaire"]),
    ("Photographie", "Conférence",
     "Couverture photo professionnelle pour conférences et séminaires.",
     120000, ["Conférence"]),
    ("Photographie", "Portrait / shooting",
     "Séance portrait en studio ou en extérieur, retouche incluse.",
     75000, []),

    # === 2. VIDÉO ===
    ("Vidéo", "Couverture vidéo événementielle",
     "Captation vidéo complète d'un événement, montage inclus.",
     300000, ["Conférence", "Autre"]),
    ("Vidéo", "Film de mariage",
     "Film cinématographique du mariage, montage et musique inclus.",
     500000, ["Mariage"]),
    ("Vidéo", "Vidéo promotionnelle",
     "Vidéo de présentation pour entreprise ou marque (2-3 minutes).",
     400000, []),
    ("Vidéo", "Interview",
     "Captation et montage d'interview (entreprise, témoignage).",
     200000, []),
    ("Vidéo", "Aftermovie",
     "Montage rétrospectif rythmé d'un événement, livré sous 5 jours.",
     250000, ["Conférence", "Mariage", "Anniversaire"]),

    # === 3. CONCEPTION GRAPHIQUE ===
    ("Conception graphique", "Affiche / flyer",
     "Création d'affiches et flyers pour événements ou promotions.",
     50000, []),
    ("Conception graphique", "Logo",
     "Création de logo professionnel avec déclinaisons.",
     100000, []),
    ("Conception graphique", "Identité visuelle",
     "Charte graphique complète : logo, palette, typographies, règles.",
     300000, []),
    ("Conception graphique", "Supports de communication",
     "Cartes de visite, en-têtes, signatures email, etc.",
     75000, []),
    ("Conception graphique", "Design pour réseaux sociaux",
     "Pack de visuels déclinés pour Instagram, Facebook, LinkedIn.",
     80000, []),

    # === 4. DÉVELOPPEMENT WEB ===
    ("Développement web", "Site vitrine",
     "Site web vitrine responsive (5 pages), hébergement non inclus.",
     400000, []),
    ("Développement web", "Application web",
     "Application web sur-mesure (gestion, espace client, etc.).",
     None, []),
    ("Développement web", "Carte de visite numérique",
     "Page web personnelle avec toutes vos infos et liens.",
     50000, []),
    ("Développement web", "Site événementiel",
     "Site dédié à un événement (mariage, conférence) avec programme.",
     200000, ["Mariage", "Conférence", "Anniversaire"]),
    ("Développement web", "Boutique / plateforme web",
     "Site e-commerce ou plateforme métier.",
     None, []),

    # === 5. COMMUNICATION DIGITALE ===
    ("Communication digitale", "Création de contenu",
     "Production de contenu (textes, visuels) pour vos réseaux.",
     150000, []),
    ("Communication digitale", "Gestion de contenu",
     "Gestion mensuelle de vos réseaux sociaux (publications, réponses).",
     200000, []),
    ("Communication digitale", "Boost Facebook",
     "Création et gestion d'une campagne publicitaire Facebook.",
     75000, []),
    ("Communication digitale", "Boost Instagram",
     "Création et gestion d'une campagne publicitaire Instagram.",
     75000, []),
    ("Communication digitale", "Campagne promotionnelle",
     "Campagne multi-canaux (Meta, Google, TikTok).",
     300000, []),

    # === 6. INVITATIONS DIGITALES ===
    ("Invitations digitales", "Invitation de mariage",
     "Invitation digitale personnalisée avec liens et détails.",
     25000, ["Mariage"]),
    ("Invitations digitales", "Save the Date",
     "Annonce digitale pour annoncer la date de votre événement.",
     15000, ["Mariage"]),
    ("Invitations digitales", "Site d'invitation",
     "Site web dédié à votre événement (RSVP, programme, plan).",
     100000, ["Mariage", "Anniversaire", "Conférence"]),
    ("Invitations digitales", "Invitation anniversaire",
     "Invitation digitale pour anniversaire (enfant, adulte).",
     20000, ["Anniversaire"]),
]


# --------------------------------------------------------------------------- #
# Champs spécifiques par prestation
# --------------------------------------------------------------------------- #
SERVICE_SPECIFIC_FIELDS = {
    # === Photographie ===
    "Photographie événementielle": [
        ("Type d'événement", "select",
         {"choices": ["Conférence", "Gala", "Cérémonie", "Autre"]}, True),
        ("Nombre de personnes attendues", "number", None, False),
        ("Durée souhaitée (heures)", "number", None, False),
        ("Style souhaité", "select",
         {"choices": ["Reportage naturel", "Posé", "Artistique"]}, False),
    ],
    "Mariage": [
        ("Date du mariage", "date", None, True),
        ("Lieu de la cérémonie", "text", None, True),
        ("Lieu de la réception", "text", None, False),
        ("Nombre d'invités", "number", None, False),
        ("Style souhaité", "select",
         {"choices": ["Reportage", "Posé", "Mixte", "Cinématographique"]}, False),
    ],
    "Anniversaire": [
        ("Âge de la personne", "number", None, False),
        ("Thème de l'anniversaire", "text", None, False),
        ("Nombre d'invités", "number", None, False),
    ],
    "Conférence": [
        ("Nom de la conférence", "text", None, True),
        ("Nombre de participants", "number", None, False),
        ("Durée (jours)", "number", None, False),
    ],
    "Portrait / shooting": [
        ("Type de portrait", "select",
         {"choices": ["Professionnel", "Personnel", "Famille", "Couple"]}, True),
        ("Nombre de personnes", "number", None, False),
        ("Lieu souhaité", "text", None, False),
    ],

    # === Vidéo ===
    "Couverture vidéo événementielle": [
        ("Type d'événement", "select",
         {"choices": ["Conférence", "Gala", "Cérémonie", "Autre"]}, True),
        ("Durée finale souhaitée (minutes)", "number", None, False),
        ("Interview à inclure ?", "select", {"choices": ["Oui", "Non"]}, False),
    ],
    "Film de mariage": [
        ("Date du mariage", "date", None, True),
        ("Durée finale souhaitée (minutes)", "number", None, False),
        ("Style souhaité", "select",
         {"choices": ["Cinématographique", "Documentaire", "Mixte"]}, False),
        ("Drone souhaité ?", "select", {"choices": ["Oui", "Non"]}, False),
    ],
    "Vidéo promotionnelle": [
        ("Secteur d'activité", "text", None, True),
        ("Durée finale souhaitée (minutes)", "number", None, False),
        ("Voix off souhaitée ?", "select", {"choices": ["Oui", "Non"]}, False),
        ("Sous-titres ?", "select", {"choices": ["Oui", "Non"]}, False),
    ],
    "Interview": [
        ("Sujet de l'interview", "text", None, True),
        ("Durée finale souhaitée (minutes)", "number", None, False),
        ("Lieu de tournage", "text", None, False),
    ],
    "Aftermovie": [
        ("Date de l'événement", "date", None, True),
        ("Durée finale souhaitée (minutes)", "number", None, False),
        ("Musique souhaitée", "text", None, False),
    ],

    # === Conception graphique ===
    "Affiche / flyer": [
        ("Type de support", "select",
         {"choices": ["Affiche A3", "Affiche A2", "Flyer A5", "Flyer A6"]}, True),
        ("Format", "select", {"choices": ["Impression", "Digital", "Les deux"]}, False),
        ("Texte à inclure", "textarea", None, False),
    ],
    "Logo": [
        ("Nom de la marque", "text", None, True),
        ("Secteur d'activité", "text", None, True),
        ("Style souhaité", "select",
         {"choices": ["Minimaliste", "Moderne", "Classique", "Créatif"]}, False),
        ("Couleurs préférées", "text", None, False),
    ],
    "Identité visuelle": [
        ("Nom de la marque", "text", None, True),
        ("Secteur d'activité", "text", None, True),
        ("Style souhaité", "select",
         {"choices": ["Minimaliste", "Moderne", "Classique", "Créatif"]}, False),
        ("Logo existant ?", "select", {"choices": ["Oui", "Non"]}, False),
    ],
    "Supports de communication": [
        ("Types de supports", "textarea", None, True),
        ("Quantité estimée", "number", None, False),
    ],
    "Design pour réseaux sociaux": [
        ("Plateformes ciblées", "textarea", None, False),
        ("Nombre de visuels", "number", None, False),
        ("Thématique", "text", None, False),
    ],

    # === Développement web ===
    "Site vitrine": [
        ("Nombre de pages", "number", None, True),
        ("Nom de domaine existant ?", "text", None, False),
        ("Fonctionnalités spécifiques", "textarea", None, False),
        ("Charte graphique existante ?", "select", {"choices": ["Oui", "Non"]}, False),
    ],
    "Application web": [
        ("Type d'application", "text", None, True),
        ("Fonctionnalités principales", "textarea", None, True),
        ("Nombre d'utilisateurs estimés", "number", None, False),
    ],
    "Carte de visite numérique": [
        ("Profession", "text", None, True),
        ("Réseaux sociaux", "textarea", None, False),
    ],
    "Site événementiel": [
        ("Nom de l'événement", "text", None, True),
        ("Date de l'événement", "date", None, True),
        ("Fonctionnalités (RSVP, programme, plan)", "textarea", None, False),
    ],
    "Boutique / plateforme web": [
        ("Type de plateforme", "text", None, True),
        ("Nombre de produits estimés", "number", None, False),
        ("Moyens de paiement souhaités", "textarea", None, False),
    ],

    # === Communication digitale ===
    "Création de contenu": [
        ("Plateformes ciblées", "textarea", None, True),
        ("Nombre de contenus par mois", "number", None, False),
        ("Thématique", "text", None, False),
    ],
    "Gestion de contenu": [
        ("Plateformes à gérer", "textarea", None, True),
        ("Fréquence de publication", "text", None, False),
        ("Durée du contrat (mois)", "number", None, False),
    ],
    "Boost Facebook": [
        ("Objectif de la campagne", "select",
         {"choices": ["Notoriété", "Trafic", "Conversions", "Engagement"]}, True),
        ("Budget publicitaire", "number", None, True),
        ("Durée (jours)", "number", None, False),
    ],
    "Boost Instagram": [
        ("Objectif de la campagne", "select",
         {"choices": ["Notoriété", "Trafic", "Conversions", "Engagement"]}, True),
        ("Budget publicitaire", "number", None, True),
        ("Durée (jours)", "number", None, False),
    ],
    "Campagne promotionnelle": [
        ("Plateformes", "textarea", None, True),
        ("Budget publicitaire", "number", None, False),
        ("Durée (jours)", "number", None, False),
    ],

    # === Invitations digitales ===
    "Invitation de mariage": [
        ("Noms des mariés", "text", None, True),
        ("Style souhaité", "select",
         {"choices": ["Élégant", "Moderne", "Traditionnel", "Minimaliste"]}, False),
    ],
    "Save the Date": [
        ("Noms des mariés", "text", None, True),
        ("Style souhaité", "text", None, False),
    ],
    "Site d'invitation": [
        ("Nom de l'événement", "text", None, True),
        ("Fonctionnalités (RSVP, programme, plan)", "textarea", None, False),
    ],
    "Invitation anniversaire": [
        ("Prénom de la personne", "text", None, True),
        ("Âge", "number", None, False),
        ("Thème", "text", None, False),
    ],
}


# --------------------------------------------------------------------------- #
# Templates d'activités par prestation
#   (nom, description, priorité, compétence, [checklist])
# --------------------------------------------------------------------------- #
ACTIVITY_TEMPLATES = {
    # === PHOTOGRAPHIE ===
    "Photographie événementielle": [
        ("Repérage du lieu", "Visite et repérage technique",
         "HAUTE", "Photography",
         ["Photos du lieu", "Notes d'éclairage", "Plan de prise de vue"]),
        ("Prise de vue — jour J", "Couverture photo de l'événement",
         "HAUTE", "Photography",
         ["Batteries chargées", "Cartes mémoire vides", "Sauvegarde des RAW"]),
        ("Post-production", "Tri, retouche et livraison",
         "NORMALE", "Photography",
         ["Sélection finale", "Retouche", "Export HD", "Livraison client"]),
    ],
    "Mariage": [
        ("Préparation", "Brief détaillé et repérage",
         "HAUTE", "Photography",
         ["Repérage cérémonie", "Repérage réception", "Brief mariés", "Planning"]),
        ("Prise de vue — préparatifs", "Photos des préparatifs",
         "HAUTE", "Photography",
         ["Préparatifs mariée", "Préparatifs marié", "Détails"]),
        ("Cérémonie", "Photos de la cérémonie",
         "HAUTE", "Photography",
         ["Entrée", "Moments clés", "Sortie"]),
        ("Cocktail et réception", "Photos des invités et de la fête",
         "HAUTE", "Photography",
         ["Photos de groupe", "Cocktail", "Première danse", "Soirée"]),
        ("Post-production", "Retouche et livraison",
         "NORMALE", "Photography",
         ["Tri", "Retouche", "Album", "Export HD", "Livraison"]),
    ],
    "Anniversaire": [
        ("Brief", "Compréhension du thème et du lieu",
         "NORMALE", "Photography",
         ["Thème validé", "Lieu confirmé", "Planning"]),
        ("Prise de vue", "Couverture photo",
         "NORMALE", "Photography",
         ["Photos invités", "Moments forts", "Détails"]),
        ("Post-production", "Tri, retouche et livraison",
         "NORMALE", "Photography",
         ["Sélection", "Retouche", "Livraison"]),
    ],
    "Conférence": [
        ("Brief", "Compréhension du programme",
         "NORMALE", "Photography",
         ["Programme reçu", "Liste intervenants", "Repérage"]),
        ("Prise de vue", "Couverture photo",
         "NORMALE", "Photography",
         ["Photos intervenants", "Photos public", "Photos networking"]),
        ("Post-production", "Tri et livraison",
         "NORMALE", "Photography",
         ["Tri", "Retouche", "Livraison"]),
    ],
    "Portrait / shooting": [
        ("Préparation du studio", "Installation lumière et fond",
         "NORMALE", "Photography",
         ["Fond installé", "Lumières réglées", "Test balance"]),
        ("Séance photo", "Prise de vue",
         "HAUTE", "Photography",
         ["Séance réalisée", "Sélection des meilleures prises"]),
        ("Retouche et livraison", "Retouche et export",
         "NORMALE", "Photography",
         ["Retouche peau", "Étalonnage", "Export", "Livraison"]),
    ],

    # === VIDÉO ===
    "Couverture vidéo événementielle": [
        ("Brief et repérage", "Compréhension de l'événement",
         "HAUTE", "Video",
         ["Brief écrit", "Repérage lieu", "Plan de tournage"]),
        ("Tournage", "Captation vidéo",
         "HAUTE", "Video",
         ["Rushes sauvegardés", "Son synchronisé", "Interviews captées"]),
        ("Montage", "Montage et post-production",
         "NORMALE", "Video Editing",
         ["Montage image", "Étalonnage", "Sound design", "Livraison"]),
    ],
    "Film de mariage": [
        ("Brief et repérage", "Repérage et planification",
         "HAUTE", "Video",
         ["Brief mariés", "Repérage lieu", "Planning tournage"]),
        ("Tournage", "Journées de tournage",
         "HAUTE", "Video",
         ["Préparatifs", "Cérémonie", "Cocktail", "Soirée"]),
        ("Montage", "Montage cinématographique",
         "HAUTE", "Video Editing",
         ["Sélection rushes", "Montage", "Sound design", "Étalonnage", "Livraison"]),
    ],
    "Vidéo promotionnelle": [
        ("Écriture du scénario", "Synopsis, script, storyboard",
         "HAUTE", "Art Direction",
         ["Synopsis", "Script", "Storyboard", "Validation"]),
        ("Préparation tournage", "Repérages et logistique",
         "HAUTE", "Video",
         ["Repérages", "Autorisations", "Planning", "Matériel"]),
        ("Tournage", "Journées de tournage",
         "HAUTE", "Video",
         ["Rushes sauvegardés", "Son synchronisé"]),
        ("Montage et post-production", "Montage final",
         "NORMALE", "Video Editing",
         ["Montage", "Sound design", "Étalonnage", "Sous-titres", "Livraison"]),
    ],
    "Interview": [
        ("Préparation", "Brief et questions",
         "NORMALE", "Video",
         ["Brief client", "Questions préparées", "Lieu confirmé"]),
        ("Tournage", "Captation de l'interview",
         "HAUTE", "Video",
         ["Rushes sauvegardés", "Son synchronisé"]),
        ("Montage", "Montage et livraison",
         "NORMALE", "Video Editing",
         ["Montage", "Sous-titres", "Livraison"]),
    ],
    "Aftermovie": [
        ("Collecte des rushes", "Récupération et tri",
         "NORMALE", "Video Editing",
         ["Rushes collectés", "Sauvegarde", "Sélection"]),
        ("Montage", "Montage rythmé",
         "HAUTE", "Video Editing",
         ["Montage image", "Choix musical", "Habillage graphique"]),
        ("Livraison", "Export et livraison",
         "NORMALE", "Video Editing",
         ["Export HD", "Export réseaux", "Livraison"]),
    ],

    # === CONCEPTION GRAPHIQUE ===
    "Affiche / flyer": [
        ("Brief créatif", "Compréhension du besoin",
         "NORMALE", "Graphic Design",
         ["Brief écrit", "Références validées"]),
        ("Création", "Production de l'affiche",
         "NORMALE", "Graphic Design",
         ["3 propositions", "Validation", "Export HD"]),
        ("Livraison", "Export et livraison",
         "NORMALE", "Graphic Design",
         ["Export print", "Export digital", "Livraison"]),
    ],
    "Logo": [
        ("Recherche créative", "Moodboard et pistes",
         "HAUTE", "Graphic Design",
         ["Moodboard", "3 pistes", "Présentation"]),
        ("Création du logo", "Déclinaisons et finalisation",
         "HAUTE", "Graphic Design",
         ["Logo principal", "Variantes", "Noir & blanc", "Fichiers sources"]),
        ("Livraison", "Export et livraison",
         "NORMALE", "Graphic Design",
         ["Export SVG", "Export PNG", "Export PDF", "Livraison"]),
    ],
    "Identité visuelle": [
        ("Recherche créative", "Moodboard et pistes",
         "HAUTE", "Graphic Design",
         ["Moodboard", "3 pistes", "Présentation"]),
        ("Création du logo", "Logo et déclinaisons",
         "HAUTE", "Graphic Design",
         ["Logo principal", "Variantes", "Fichiers sources"]),
        ("Charte graphique", "Document de référence",
         "NORMALE", "Graphic Design",
         ["Palette", "Typographies", "Règles", "Exemples"]),
        ("Livraison", "Export et livraison",
         "NORMALE", "Graphic Design",
         ["Export final", "Livraison"]),
    ],
    "Supports de communication": [
        ("Brief créatif", "Compréhension du besoin",
         "NORMALE", "Graphic Design",
         ["Liste des supports", "Charte disponible"]),
        ("Création", "Production des supports",
         "NORMALE", "Graphic Design",
         ["Cartes de visite", "En-têtes", "Signatures email"]),
        ("Livraison", "Export et livraison",
         "NORMALE", "Graphic Design",
         ["Export print", "Export digital", "Livraison"]),
    ],
    "Design pour réseaux sociaux": [
        ("Brief créatif", "Compréhension du besoin",
         "NORMALE", "Graphic Design",
         ["Brief écrit", "Références validées"]),
        ("Création des visuels", "Production des visuels",
         "NORMALE", "Graphic Design",
         ["Visuels produits", "Déclinaisons", "Export"]),
    ],

    # === DÉVELOPPEMENT WEB ===
    "Site vitrine": [
        ("Cadrage", "Recueil des besoins et arborescence",
         "HAUTE", "Web Development",
         ["Arborescence validée", "Contenus fournis", "Charte disponible"]),
        ("Design des maquettes", "Maquettes desktop et mobile",
         "HAUTE", "Web Development",
         ["Maquette desktop", "Maquette mobile", "Validation"]),
        ("Intégration", "Développement HTML/CSS/JS",
         "HAUTE", "Web Development",
         ["Intégration responsive", "Test navigateurs", "Optimisation"]),
        ("Mise en ligne", "Déploiement",
         "NORMALE", "Web Development",
         ["Domaine configuré", "HTTPS actif", "Sitemap", "Analytics"]),
    ],
    "Application web": [
        ("Cadrage", "Définition des besoins",
         "HAUTE", "Web Development",
         ["Cahier des charges", "Wireframes", "Validation"]),
        ("Design", "Maquettes et UX",
         "HAUTE", "UI/UX Design",
         ["Maquettes", "Parcours utilisateur", "Validation"]),
        ("Développement", "Développement de l'application",
         "HAUTE", "Web Development",
         ["Backend", "Frontend", "Base de données", "Tests"]),
        ("Déploiement", "Mise en ligne",
         "NORMALE", "Web Development",
         ["Serveur configuré", "Domaine", "HTTPS", "Sauvegardes"]),
    ],
    "Carte de visite numérique": [
        ("Collecte des informations", "Infos du client",
         "NORMALE", "Web Development",
         ["Nom", "Profession", "Contacts", "Réseaux"]),
        ("Création", "Design et développement",
         "NORMALE", "UI/UX Design",
         ["Design", "Développement", "Validation"]),
        ("Livraison", "Mise en ligne",
         "NORMALE", "Web Development",
         ["Hébergement", "URL", "QR code", "Livraison"]),
    ],
    "Site événementiel": [
        ("Cadrage", "Compréhension de l'événement",
         "HAUTE", "Web Development",
         ["Brief", "Programme", "Fonctionnalités"]),
        ("Design et développement", "Création du site",
         "HAUTE", "Web Development",
         ["Maquettes", "Développement", "Validation"]),
        ("Mise en ligne", "Déploiement",
         "NORMALE", "Web Development",
         ["Domaine", "HTTPS", "Tests"]),
    ],
    "Boutique / plateforme web": [
        ("Cadrage", "Définition des besoins",
         "HAUTE", "Web Development",
         ["Cahier des charges", "Modèle économique", "Validation"]),
        ("Design", "Maquettes et UX",
         "HAUTE", "UI/UX Design",
         ["Maquettes", "Parcours d'achat", "Validation"]),
        ("Développement", "Développement de la plateforme",
         "HAUTE", "Web Development",
         ["Backend", "Frontend", "Paiement", "Tests"]),
        ("Déploiement", "Mise en ligne",
         "NORMALE", "Web Development",
         ["Serveur", "Domaine", "HTTPS", "Formation"]),
    ],

    # === COMMUNICATION DIGITALE ===
    "Création de contenu": [
        ("Stratégie éditoriale", "Définition du ton et des thèmes",
         "HAUTE", "Community Management",
         ["Ton défini", "Thèmes", "Calendrier"]),
        ("Production de contenu", "Création des visuels et textes",
         "HAUTE", "Copywriting",
         ["Textes", "Visuels", "Validation"]),
        ("Livraison", "Livraison du contenu",
         "NORMALE", "Community Management",
         ["Export", "Livraison"]),
    ],
    "Gestion de contenu": [
        ("Stratégie", "Définition de la stratégie",
         "HAUTE", "Community Management",
         ["Audit", "Objectifs", "Calendrier"]),
        ("Production mensuelle", "Création et planification",
         "HAUTE", "Community Management",
         ["Contenus du mois", "Planification", "Publications"]),
        ("Suivi et reporting", "Analyse des performances",
         "NORMALE", "Community Management",
         ["Rapport mensuel", "Recommandations"]),
    ],
    "Boost Facebook": [
        ("Stratégie", "Définition des audiences",
         "HAUTE", "Digital Advertising",
         ["Audiences", "Objectifs", "Budget"]),
        ("Création des annonces", "Visuels et textes",
         "HAUTE", "Digital Advertising",
         ["3 visuels", "3 textes", "Validation"]),
        ("Lancement et suivi", "Campagne et optimisation",
         "HAUTE", "Digital Advertising",
         ["Campagne lancée", "Suivi quotidien", "Rapport"]),
    ],
    "Boost Instagram": [
        ("Stratégie", "Définition des audiences",
         "HAUTE", "Digital Advertising",
         ["Audiences", "Objectifs", "Budget"]),
        ("Création des annonces", "Visuels et textes",
         "HAUTE", "Digital Advertising",
         ["3 visuels", "3 textes", "Validation"]),
        ("Lancement et suivi", "Campagne et optimisation",
         "HAUTE", "Digital Advertising",
         ["Campagne lancée", "Suivi quotidien", "Rapport"]),
    ],
    "Campagne promotionnelle": [
        ("Stratégie", "Définition des canaux et audiences",
         "HAUTE", "Digital Advertising",
         ["Audiences", "Canaux", "Budget", "Objectifs"]),
        ("Création", "Création des supports",
         "HAUTE", "Digital Advertising",
         ["Visuels", "Textes", "Validation"]),
        ("Lancement et suivi", "Lancement et optimisation",
         "HAUTE", "Digital Advertising",
         ["Campagne lancée", "Suivi", "Rapport"]),
    ],

    # === INVITATIONS DIGITALES ===
    "Invitation de mariage": [
        ("Collecte des informations", "Détails du mariage",
         "NORMALE", "Graphic Design",
         ["Noms", "Date", "Lieu", "Détails"]),
        ("Design", "Création de l'invitation",
         "NORMALE", "Graphic Design",
         ["Proposition", "Validation", "Finalisation"]),
        ("Livraison", "Export et livraison",
         "NORMALE", "Graphic Design",
         ["Export HD", "Export réseaux", "Livraison"]),
    ],
    "Save the Date": [
        ("Collecte des informations", "Date du mariage",
         "NORMALE", "Graphic Design",
         ["Noms", "Date", "Style"]),
        ("Design", "Création du Save the Date",
         "NORMALE", "Graphic Design",
         ["Proposition", "Validation", "Finalisation"]),
        ("Livraison", "Export et livraison",
         "NORMALE", "Graphic Design",
         ["Export", "Livraison"]),
    ],
    "Site d'invitation": [
        ("Cadrage", "Définition du contenu",
         "HAUTE", "Web Development",
         ["Contenu", "Fonctionnalités", "Validation"]),
        ("Design et développement", "Création du site",
         "HAUTE", "Web Development",
         ["Maquettes", "Développement", "Validation"]),
        ("Mise en ligne", "Déploiement",
         "NORMALE", "Web Development",
         ["Domaine", "Tests", "Livraison"]),
    ],
    "Invitation anniversaire": [
        ("Collecte des informations", "Détails de l'anniversaire",
         "NORMALE", "Graphic Design",
         ["Prénom", "Âge", "Date", "Lieu"]),
        ("Design", "Création de l'invitation",
         "NORMALE", "Graphic Design",
         ["Proposition", "Validation"]),
        ("Livraison", "Export et livraison",
         "NORMALE", "Graphic Design",
         ["Export", "Livraison"]),
    ],
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _get_or_create(db, model, defaults=None, **filters):
    """Récupère ou crée une ligne (idempotent)."""
    obj = db.query(model).filter_by(**filters).one_or_none()
    if obj is None:
        params = {**filters, **(defaults or {})}
        obj = model(**params)
        db.add(obj)
        db.flush()
    return obj


# --------------------------------------------------------------------------- #
# Seed
# --------------------------------------------------------------------------- #
def run() -> None:
    db = SessionLocal()
    try:
        # ------------------------------------------------------------------ #
        # 1. Rôles
        # ------------------------------------------------------------------ #
        role_objs = {}
        for role_name in ROLES:
            role_objs[role_name] = _get_or_create(db, Role, name=role_name)

        # ------------------------------------------------------------------ #
        # 2. Permissions
        # ------------------------------------------------------------------ #
        for role_name, codes in PERMISSIONS_BY_ROLE.items():
            for code in codes:
                perm = _get_or_create(db, Permission, code=code)
                exists = (
                    db.query(RolePermission)
                    .filter_by(role_id=role_objs[role_name].id, permission_id=perm.id)
                    .one_or_none()
                )
                if exists is None:
                    db.add(RolePermission(
                        role_id=role_objs[role_name].id,
                        permission_id=perm.id,
                    ))
        db.flush()

        # ------------------------------------------------------------------ #
        # 3. Catégories
        # ------------------------------------------------------------------ #
        cat_objs = {}
        for name in CATEGORIES:
            cat_objs[name] = _get_or_create(
                db, Category, name=name, defaults={"is_active": True},
            )

        # ------------------------------------------------------------------ #
        # 4. Types d'événements
        # ------------------------------------------------------------------ #
        et_objs = {}
        for name in EVENT_TYPES:
            et_objs[name] = _get_or_create(db, EventType, name=name)

        # ------------------------------------------------------------------ #
        # 5. Compétences
        # ------------------------------------------------------------------ #
        skill_objs = {}
        for name in SKILLS:
            skill_objs[name] = _get_or_create(db, Skill, name=name)

        db.flush()

        # ------------------------------------------------------------------ #
        # 6. Postes
        # ------------------------------------------------------------------ #
        for pos_data in POSITIONS:
            position = _get_or_create(
                db, Position,
                name=pos_data["name"],
                defaults={
                    "description": pos_data["description"],
                    "display_order": pos_data["order"],
                    "is_active": True,
                },
            )
            for skill_name in pos_data["skills"]:
                skill = skill_objs.get(skill_name)
                if skill is None:
                    continue
                exists = (
                    db.query(PositionSkill)
                    .filter_by(position_id=position.id, skill_id=skill.id)
                    .one_or_none()
                )
                if exists is None:
                    db.add(PositionSkill(position_id=position.id, skill_id=skill.id))

        db.flush()

        # ------------------------------------------------------------------ #
        # 7. Plateformes
        # ------------------------------------------------------------------ #
        for name in PLATFORMS:
            _get_or_create(db, Platform, name=name)

        # ------------------------------------------------------------------ #
        # 8. Champs de formulaire communs
        # ------------------------------------------------------------------ #
        common_fields = {}
        for label, ftype, options, _required in COMMON_FORM_FIELDS:
            common_fields[label] = _get_or_create(
                db, FormField,
                label=label,
                defaults={"field_type": ftype, "options": options},
            )
        db.flush()

        # ------------------------------------------------------------------ #
        # 9. Prestations
        # ------------------------------------------------------------------ #
        for cat_name, svc_name, svc_desc, svc_price, svc_event_types in SERVICES:
            svc = _get_or_create(
                db, Service,
                name=svc_name,
                defaults={
                    "category_id": cat_objs[cat_name].id,
                    "description": svc_desc,
                    "base_price": svc_price,
                    "is_active": True,
                },
            )

            # Champs communs
            order = 0
            for label, _ftype, _options, required in COMMON_FORM_FIELDS:
                ff = common_fields[label]
                exists = (
                    db.query(ServiceFormField)
                    .filter_by(service_id=svc.id, form_field_id=ff.id)
                    .one_or_none()
                )
                if exists is None:
                    db.add(ServiceFormField(
                        service_id=svc.id,
                        form_field_id=ff.id,
                        display_order=order,
                        is_required=required,
                    ))
                    order += 1

            # Champs spécifiques — CORRIGÉ : réutilise le champ s'il existe déjà
            for label, ftype, options, required in SERVICE_SPECIFIC_FIELDS.get(svc_name, []):
                ff = common_fields.get(label)
                if ff is None:
                    ff = _get_or_create(
                        db, FormField,
                        label=label,
                        defaults={"field_type": ftype, "options": options},
                    )

                exists = (
                    db.query(ServiceFormField)
                    .filter_by(service_id=svc.id, form_field_id=ff.id)
                    .one_or_none()
                )
                if exists is None:
                    db.add(ServiceFormField(
                        service_id=svc.id,
                        form_field_id=ff.id,
                        display_order=order,
                        is_required=required,
                    ))
                    order += 1

            # Liaison prestation ↔ types d'événements
            for et_name in svc_event_types:
                et = et_objs.get(et_name)
                if et is None:
                    continue
                exists = (
                    db.query(ServiceEventType)
                    .filter_by(service_id=svc.id, event_type_id=et.id)
                    .one_or_none()
                )
                if exists is None:
                    db.add(ServiceEventType(
                        service_id=svc.id,
                        event_type_id=et.id,
                    ))

            # Templates d'activités
            for idx, (at_name, at_desc, at_prio, at_skill, checklist) in enumerate(
                ACTIVITY_TEMPLATES.get(svc_name, [])
            ):
                priority_value = getattr(ActivityPriority, at_prio, ActivityPriority.NORMALE)

                at = _get_or_create(
                    db, ActivityTemplate,
                    service_id=svc.id, name=at_name,
                    defaults={
                        "description": at_desc,
                        "priority": priority_value,
                        "required_skill_id": skill_objs[at_skill].id if at_skill in skill_objs else None,
                        "display_order": idx,
                        "is_active": True,
                    },
                )

                for c_idx, item_label in enumerate(checklist):
                    exists = (
                        db.query(ChecklistTemplateItem)
                        .filter_by(activity_template_id=at.id, label=item_label)
                        .one_or_none()
                    )
                    if exists is None:
                        db.add(ChecklistTemplateItem(
                            activity_template_id=at.id,
                            label=item_label,
                            display_order=c_idx,
                        ))

        # ------------------------------------------------------------------ #
        # 10. Canal #général (chat)
        # ------------------------------------------------------------------ #
        global_channel = (
            db.query(Channel)
            .filter(Channel.type == ChannelType.GLOBAL)
            .one_or_none()
        )
        if global_channel is None:
            db.add(Channel(name="Général", type=ChannelType.GLOBAL))

        db.commit()
        print("✅ Seed terminé :")
        print("   • rôles (CEO, DA, CM) et permissions")
        print("   • postes (8) avec leurs compétences typiques")
        print(f"   • compétences ({len(SKILLS)})")
        print(f"   • catégories ({len(CATEGORIES)})")
        print(f"   • prestations ({len(SERVICES)})")
        print("   • champs de formulaire + templates d'activités")
        print("   • canal #général (chat)")

    except Exception as e:
        db.rollback()
        print(f"❌ Erreur pendant le seed : {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()