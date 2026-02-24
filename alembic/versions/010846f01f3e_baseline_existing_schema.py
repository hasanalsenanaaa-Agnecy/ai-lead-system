"""baseline_existing_schema

Baseline migration representing all 13 tables as they exist in the database.
This was created to establish Alembic tracking on an existing database.
If the database already has these tables, stamp instead of running:
    alembic stamp 010846f01f3e

Revision ID: 010846f01f3e
Revises: 
Create Date: 2026-02-19 01:01:18.789159

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, TIMESTAMP


# revision identifiers, used by Alembic.
revision: str = '010846f01f3e'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables from scratch (for fresh deployments)."""

    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 1. clients
    op.create_table(
        'clients',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('industry', sa.String(100)),
        sa.Column('website', sa.String(500)),
        sa.Column('phone_number', sa.String(20)),
        sa.Column('whatsapp_number', sa.String(20)),
        sa.Column('email', sa.String(255)),
        sa.Column('status', sa.String(50), nullable=False, server_default='onboarding'),
        sa.Column('timezone', sa.String(50), nullable=False, server_default='UTC'),
        sa.Column('primary_language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('api_key_hash', sa.String(255)),
        sa.Column('webhook_secret_hash', sa.String(255)),
        sa.Column('config', JSONB, nullable=False, server_default='{}'),
        sa.Column('plan', sa.String(50), nullable=False, server_default='starter'),
        sa.Column('monthly_token_budget', sa.Integer, nullable=False, server_default='500000'),
        sa.Column('tokens_used_this_month', sa.Integer, nullable=False, server_default='0'),
        sa.Column('token_reset_date', TIMESTAMP(timezone=True)),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', TIMESTAMP(timezone=True)),
    )

    # 2. users
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('client_id', UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE')),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='agent'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('two_factor_enabled', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('two_factor_secret', sa.String(255)),
        sa.Column('backup_codes', ARRAY(sa.String)),
        sa.Column('login_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('failed_login_attempts', sa.Integer, nullable=False, server_default='0'),
        sa.Column('locked_until', TIMESTAMP(timezone=True)),
        sa.Column('last_login_at', TIMESTAMP(timezone=True)),
        sa.Column('last_login_ip', sa.String(45)),
        sa.Column('timezone', sa.String(50), nullable=False, server_default='UTC'),
        sa.Column('language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('avatar_url', sa.String(500)),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', TIMESTAMP(timezone=True)),
    )
    op.create_index('ix_users_client_id', 'users', ['client_id'])
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_is_active', 'users', ['is_active'])
    op.create_index('ix_users_role', 'users', ['role'])

    # 3. user_sessions
    op.create_table(
        'user_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('refresh_token_hash', sa.String(255), nullable=False),
        sa.Column('device_info', sa.String(500)),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.Text),
        sa.Column('remember_me', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_valid', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('expires_at', TIMESTAMP(timezone=True), nullable=False),
        sa.Column('last_activity_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('ix_user_sessions_refresh_token_hash', 'user_sessions', ['refresh_token_hash'])
    op.create_index('ix_user_sessions_is_valid', 'user_sessions', ['is_valid'])
    op.create_index('ix_user_sessions_expires_at', 'user_sessions', ['expires_at'])

    # 4. audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('client_id', UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='SET NULL')),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50)),
        sa.Column('resource_id', sa.String(255)),
        sa.Column('details', sa.Text),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.Text),
        sa.Column('severity', sa.String(20), nullable=False, server_default='info'),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_client_id', 'audit_logs', ['client_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])

    # 5. leads
    op.create_table(
        'leads',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('client_id', UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('first_name', sa.String(100)),
        sa.Column('last_name', sa.String(100)),
        sa.Column('email', sa.String(255)),
        sa.Column('phone', sa.String(20)),
        sa.Column('company', sa.String(255)),
        sa.Column('source_channel', sa.String(50), nullable=False),
        sa.Column('source_campaign', sa.String(255)),
        sa.Column('source_medium', sa.String(100)),
        sa.Column('status', sa.String(50), nullable=False, server_default='new'),
        sa.Column('score', sa.String(20), nullable=False, server_default='unscored'),
        sa.Column('score_value', sa.Integer, nullable=False, server_default='0'),
        sa.Column('qualification_data', JSONB, nullable=False, server_default='{}'),
        sa.Column('service_interest', sa.String(255)),
        sa.Column('urgency', sa.String(50)),
        sa.Column('budget_range', sa.String(100)),
        sa.Column('location', sa.String(255)),
        sa.Column('decision_maker', sa.Boolean),
        sa.Column('timeline', sa.String(100)),
        sa.Column('preferred_contact_time', sa.String(255)),
        sa.Column('tags', ARRAY(sa.String)),
        sa.Column('lead_metadata', JSONB, nullable=False, server_default='{}'),
        sa.Column('assigned_to', UUID(as_uuid=True)),
        sa.Column('appointment_at', TIMESTAMP(timezone=True)),
        sa.Column('crm_id', sa.String(255)),
        sa.Column('crm_synced_at', TIMESTAMP(timezone=True)),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', TIMESTAMP(timezone=True)),
    )
    op.create_index('ix_leads_client_id', 'leads', ['client_id'])
    op.create_index('ix_leads_email', 'leads', ['email'])
    op.create_index('ix_leads_phone', 'leads', ['phone'])
    op.create_index('ix_leads_status', 'leads', ['status'])
    op.create_index('ix_leads_score', 'leads', ['score'])
    op.create_index('ix_leads_created_at', 'leads', ['created_at'])
    op.create_index('ix_leads_client_status', 'leads', ['client_id', 'status'])

    # 6. conversations
    op.create_table(
        'conversations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('client_id', UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('lead_id', UUID(as_uuid=True), sa.ForeignKey('leads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('channel_conversation_id', sa.String(255)),
        sa.Column('session_id', sa.String(255)),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('is_escalated', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('escalation_reason', sa.String(100)),
        sa.Column('message_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('last_message_at', TIMESTAMP(timezone=True)),
        sa.Column('ended_at', TIMESTAMP(timezone=True)),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_conversations_client_id', 'conversations', ['client_id'])
    op.create_index('ix_conversations_lead_id', 'conversations', ['lead_id'])
    op.create_index('ix_conversations_is_active', 'conversations', ['is_active'])

    # 7. messages
    op.create_table(
        'messages',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('conversation_id', UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('content_type', sa.String(20), nullable=False, server_default='text'),
        sa.Column('channel', sa.String(50)),
        sa.Column('external_message_id', sa.String(255)),
        sa.Column('tokens_input', sa.Integer, nullable=False, server_default='0'),
        sa.Column('tokens_output', sa.Integer, nullable=False, server_default='0'),
        sa.Column('model_used', sa.String(100)),
        sa.Column('confidence_score', sa.Float),
        sa.Column('processing_time_ms', sa.Integer),
        sa.Column('intent', sa.String(100)),
        sa.Column('sentiment', sa.String(50)),
        sa.Column('entities', JSONB),
        sa.Column('message_metadata', JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_index('ix_messages_role', 'messages', ['role'])
    op.create_index('ix_messages_created_at', 'messages', ['created_at'])

    # 8. knowledge_bases
    op.create_table(
        'knowledge_bases',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('client_id', UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('category', sa.String(100), nullable=False, server_default='general'),
        sa.Column('source_type', sa.String(50), nullable=False, server_default='document'),
        sa.Column('source_url', sa.String(500)),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('chunk_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('document_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_knowledge_bases_client_id', 'knowledge_bases', ['client_id'])
    op.create_index('ix_knowledge_bases_category', 'knowledge_bases', ['category'])

    # 9. knowledge_chunks
    op.create_table(
        'knowledge_chunks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('knowledge_base_id', UUID(as_uuid=True), sa.ForeignKey('knowledge_bases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('client_id', UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('content_hash', sa.String(64)),
        sa.Column('token_count', sa.Integer, nullable=False),
        sa.Column('source', sa.String(500)),
        sa.Column('embedding', Vector(1536)),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('chunk_index', sa.Integer, nullable=False),
        sa.Column('metadata', JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_knowledge_chunks_knowledge_base_id', 'knowledge_chunks', ['knowledge_base_id'])
    op.create_index('ix_knowledge_chunks_client_id', 'knowledge_chunks', ['client_id'])
    op.execute("""
        CREATE INDEX ix_knowledge_chunks_embedding 
        ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10)
    """)

    # 10. escalations
    op.create_table(
        'escalations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('client_id', UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('lead_id', UUID(as_uuid=True), sa.ForeignKey('leads.id', ondelete='CASCADE')),
        sa.Column('conversation_id', UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='CASCADE')),
        sa.Column('reason', sa.String(100), nullable=False),
        sa.Column('priority', sa.String(20), nullable=False, server_default='medium'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('assigned_to', UUID(as_uuid=True)),
        sa.Column('resolution_notes', sa.Text),
        sa.Column('resolved_at', TIMESTAMP(timezone=True)),
        sa.Column('resolved_by', UUID(as_uuid=True)),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_escalations_client_id', 'escalations', ['client_id'])
    op.create_index('ix_escalations_status', 'escalations', ['status'])
    op.create_index('ix_escalations_created_at', 'escalations', ['created_at'])

    # 11. qualification_rules
    op.create_table(
        'qualification_rules',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('client_id', UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(50), nullable=False, server_default='general'),
        sa.Column('condition_field', sa.String(100), nullable=False),
        sa.Column('condition_operator', sa.String(20), nullable=False),
        sa.Column('condition_value', sa.String(255), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('action_value', sa.String(255)),
        sa.Column('priority', sa.Integer, nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('score_impact', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_qualification_rules_client_id', 'qualification_rules', ['client_id'])
    op.create_index('ix_qualification_rules_category', 'qualification_rules', ['category'])
    op.create_index('ix_qualification_rules_is_active', 'qualification_rules', ['is_active'])

    # 12. usage_logs
    op.create_table(
        'usage_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('client_id', UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('conversation_id', UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='SET NULL')),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('tokens_input', sa.Integer, nullable=False),
        sa.Column('tokens_output', sa.Integer, nullable=False),
        sa.Column('cost_microdollars', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_usage_logs_client_created', 'usage_logs', ['client_id', 'created_at'])

    # 13. rate_limit_records
    op.create_table(
        'rate_limit_records',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('key', sa.String(255), nullable=False),
        sa.Column('request_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('window_start', TIMESTAMP(timezone=True), nullable=False),
        sa.Column('window_end', TIMESTAMP(timezone=True), nullable=False),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_rate_limit_window', 'rate_limit_records', ['window_start', 'window_end'])


def downgrade() -> None:
    """Drop all tables (reverse order for foreign keys)."""
    op.drop_table('rate_limit_records')
    op.drop_table('usage_logs')
    op.drop_table('qualification_rules')
    op.drop_table('escalations')
    op.drop_table('knowledge_chunks')
    op.drop_table('knowledge_bases')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('leads')
    op.drop_table('audit_logs')
    op.drop_table('user_sessions')
    op.drop_table('users')
    op.drop_table('clients')
    op.execute("DROP EXTENSION IF EXISTS vector")
