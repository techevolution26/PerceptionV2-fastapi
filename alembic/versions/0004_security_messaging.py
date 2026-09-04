"""security, google identity, message lifecycle, admin audit and legacy repair"""
from typing import Sequence, Union
import json
import sqlalchemy as sa
from alembic import op
revision="0004_security_messaging"; down_revision="0003_stripe_billing"; branch_labels=None; depends_on=None

def upgrade():
    op.add_column("users",sa.Column("google_sub",sa.String(255),nullable=True)); op.create_index("ix_users_google_sub","users",["google_sub"],unique=True)
    op.add_column("users",sa.Column("token_version",sa.Integer(),nullable=False,server_default="0")); op.add_column("users",sa.Column("is_active",sa.Boolean(),nullable=False,server_default=sa.true()))
    op.add_column("messages",sa.Column("edited_at",sa.DateTime(timezone=True),nullable=True)); op.add_column("messages",sa.Column("deleted_at",sa.DateTime(timezone=True),nullable=True))
    op.create_table("conversation_states",sa.Column("user_id",sa.Integer(),sa.ForeignKey("users.id",ondelete="CASCADE"),primary_key=True),sa.Column("peer_id",sa.Integer(),sa.ForeignKey("users.id",ondelete="CASCADE"),primary_key=True),sa.Column("archived_at",sa.DateTime(timezone=True)),sa.Column("deleted_at",sa.DateTime(timezone=True)),sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now()))
    op.create_index("ix_conversation_state_user","conversation_states",["user_id"])
    op.create_table("admin_audit_logs",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("actor_user_id",sa.Integer(),sa.ForeignKey("users.id",ondelete="RESTRICT"),nullable=False),sa.Column("action",sa.String(128),nullable=False),sa.Column("target_user_id",sa.Integer(),sa.ForeignKey("users.id",ondelete="SET NULL")),sa.Column("data",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()))
    for name,col in [("actor","actor_user_id"),("action","action"),("target","target_user_id")]: op.create_index(f"ix_admin_audit_logs_{name}","admin_audit_logs",[col])
    conn=op.get_bind(); topics={r.name:r.id for r in conn.execute(sa.text("SELECT id,name FROM topics"))}
    for r in conn.execute(sa.text("SELECT id,analytics_specialties FROM users")).mappings():
        v=r["analytics_specialties"] or []
        if isinstance(v,list) and any(isinstance(x,str) for x in v):
            normalized=list(dict.fromkeys(topics[x] for x in v if x in topics))
            conn.execute(sa.text("UPDATE users SET analytics_specialties=CAST(:v AS json) WHERE id=:id"),{"v":json.dumps(normalized),"id":r["id"]})

def downgrade():
    for name in ["target","action","actor"]: op.drop_index(f"ix_admin_audit_logs_{name}",table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs"); op.drop_index("ix_conversation_state_user",table_name="conversation_states"); op.drop_table("conversation_states")
    op.drop_column("messages","deleted_at"); op.drop_column("messages","edited_at"); op.drop_column("users","is_active"); op.drop_column("users","token_version"); op.drop_index("ix_users_google_sub",table_name="users"); op.drop_column("users","google_sub")
