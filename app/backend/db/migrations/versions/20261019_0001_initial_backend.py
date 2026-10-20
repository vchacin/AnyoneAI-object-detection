"""Create the multi-tenant backend schema."""
from alembic import op

from app.backend.db.session import Base
from app.backend.db import models  # noqa: F401

revision = "20261019_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
