"""
Importer tous les modules de modèles ici garantit que la registry SQLAlchemy
(nécessaire pour résoudre les relationships déclarées en chaînes de caractères,
ex. Mapped["Project"]) connaît toutes les classes avant que les mappers ne
soient configurés — indispensable pour Alembic --autogenerate.
"""

from app.models.auth import (  # noqa: F401
    AuditLog,
    OwnershipStatus,
    PasswordResetToken,
    Permission,
    Position,
    PositionSkill,
    Role,
    RolePermission,
    SecurityEvent,
    Skill,
    User,
    UserPosition,
    UserSkill,
)
from app.models.business import (  # noqa: F401
    Category,
    Client,
    EventType,
    FormField,
    Service,
    ServiceEventType,
    ServiceFormField,
)
from app.models.cash import (  # noqa: F401
    CashClosing,
    CashTransaction,
)
from app.models.chat import (  # noqa: F401
    Channel,
    ChannelMember,
    ChannelType,
    Message,
)
from app.models.content import (  # noqa: F401
    PortfolioItem,
    Platform,
    Publication,
    PublicationFormat,
    PublicationPlatform,
    PublicationStatus,
)
from app.models.dev import DevMembership  # noqa: F401
from app.models.finance import (  # noqa: F401
    Payment,
    Remuneration,
    Revenue,
)
from app.models.workflow import (  # noqa: F401
    Activity,
    ActivityAssignment,
    ActivityChecklist,
    ActivityPriority,
    ActivityStatus,
    ActivityTemplate,
    AssignmentRole,
    ChecklistTemplateItem,
    Document,
    Notification,
    Project,
    ProjectCategory,
    ProjectService,
    ProjectServiceStatus,
    ProjectStatus,
    ProjectType,
    Request,
    RequestStatus,
    RequestStatusHistory,
)