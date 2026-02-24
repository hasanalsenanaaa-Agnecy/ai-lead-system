"""Initial migration - all tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clients table
    op.create_table(
        'clients',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='onboarding'),
        sa.Column('industry', sa.String(100)),
        sa.Column('website', sa.String(500)),
        sa.Column('timezone', sa.String(50), server_default='America/New_York'),
        sa.Column('primary_language', sa.String(10), server_default='en'),
        sa.Column('owner_name', sa.String(255)),
        sa.Column('owner_email', sa.String(255)),
        sa.Column('owner_phone', sa.String(50)),
        sa.Column('config', postgresql.JSON, server_default='{}'),
        sa.Column('plan', sa.String(50), server_default='growth'),
        sa.Column('monthly_token_budget', sa.Integer, server_default='1000000'),
        sa.Column('tokens_used_this_month', sa.Integer, server_default='0'),
        sa.Column('billing_cycle_start', sa.DateTime(timezone=True)),
        sa.Column('api_key_hash', sa.String(255)),
        sa.Column('webhook_secret_hash', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_clients_slug', 'clients', ['slug'])
    op.create_index('ix_clients_status', 'clients', ['status'])

    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE')),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('phone', sa.String(50)),
        sa.Column('avatar_url', sa.String(500)),
        sa.Column('role', sa.String(50), nullable=False, server_default='agent'),
        sa.Column('permissions', sa.Text),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('is_verified', sa.Boolean, server_default='false'),
        sa.Column('email_verified_at', sa.DateTime(timezone=True)),
        sa.Column('verification_token', sa.String(255)),
        sa.Column('verification_token_expires', sa.DateTime(timezone=True)),
        sa.Column('password_reset_token', sa.String(255)),
        sa.Column('password_reset_expires', sa.DateTime(timezone=True)),
        sa.Column('password_changed_at', sa.DateTime(timezone=True)),
        sa.Column('two_factor_enabled', sa.Boolean, server_default='false'),
        sa.Column('two_factor_secret', sa.String(255)),
        sa.Column('two_factor_backup_codes', sa.Text),
        sa.Column('last_login_at', sa.DateTime(timezone=True)),
        sa.Column('last_login_ip', sa.String(45)),
        sa.Column('login_count', sa.Integer, server_default='0'),
        sa.Column('failed_login_attempts', sa.Integer, server_default='0'),
        sa.Column('locked_until', sa.DateTime(timezone=True)),
        sa.Column('timezone', sa.String(50), server_default='Asia/Riyadh'),
        sa.Column('language', sa.String(10), server_default='en'),
        sa.Column('notification_preferences', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_client_id', 'users', ['client_id'])
    op.create_index('ix_users_role', 'users', ['role'])

    # User Sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('refresh_token_hash', sa.String(255), nullable=False),
        sa.Column('access_token_hash', sa.String(255)),
        sa.Column('device_info', sa.String(500)),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('remember_me', sa.Boolean, server_default='false'),
        sa.Column('is_valid', sa.Boolean, server_default='true'),
        sa.Column('invalidated_at', sa.DateTime(timezone=True)),
        sa.Column('invalidation_reason', sa.String(100)),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('ix_user_sessions_refresh_token_hash', 'user_sessions', ['refresh_token_hash'])

    # Leads table
    op.create_table(
        'leads',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('phone', sa.String(50), index=True),
        sa.Column('email', sa.String(255), index=True),
        sa.Column('name', sa.String(255)),
        sa.Column('first_name', sa.String(100)),
        sa.Column('last_name', sa.String(100)),
        sa.Column('source_channel', sa.String(50), nullable=False),
        sa.Column('source_campaign', sa.String(255)),
        sa.Column('source_medium', sa.String(100)),
        sa.Column('landing_page', sa.String(500)),
        sa.Column('status', sa.String(50), nullable=False, server_default='new'),
        sa.Column('score', sa.String(50), nullable=False, server_default='unscored'),
        sa.Column('score_value', sa.Integer, server_default='0'),
        sa.Column('qualification_data', postgresql.JSON, server_default='{}'),
        sa.Column('service_interest', sa.String(255)),
        sa.Column('budget_range', sa.String(100)),
        sa.Column('urgency', sa.String(100)),
        sa.Column('location', sa.String(255)),
        sa.Column('preferred_contact_time', sa.String(100)),
        sa.Column('notes', sa.Text),
        sa.Column('lead_metadata', postgresql.JSON, server_default='{}'),
        sa.Column('appointment_at', sa.DateTime(timezone=True)),
        sa.Column('appointment_notes', sa.Text),
        sa.Column('handed_off_at', sa.DateTime(timezone=True)),
        sa.Column('handed_off_to', sa.String(255)),
        sa.Column('crm_contact_id', sa.String(255)),
        sa.Column('crm_synced_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_leads_client_id', 'leads', ['client_id'])
    op.create_index('ix_leads_status', 'leads', ['status'])
    op.create_index('ix_leads_score', 'leads', ['score'])
    op.create_index('ix_leads_created_at', 'leads', ['created_at'])

    # Conversations table
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('leads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('session_id', sa.String(255)),
        sa.Column('external_conversation_id', sa.String(255)),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('is_escalated', sa.Boolean, server_default='false'),
        sa.Column('escalation_reason', sa.String(100)),
        sa.Column('escalation_details', sa.Text),
        sa.Column('escalated_at', sa.DateTime(timezone=True)),
        sa.Column('message_count', sa.Integer, server_default='0'),
        sa.Column('summary', sa.Text),
        sa.Column('sentiment_score', sa.Float),
        sa.Column('ended_at', sa.DateTime(timezone=True)),
        sa.Column('end_reason', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_conversations_client_id', 'conversations', ['client_id'])
    op.create_index('ix_conversations_lead_id', 'conversations', ['lead_id'])
    op.create_index('ix_conversations_is_active', 'conversations', ['is_active'])

    # Messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('content_type', sa.String(50), server_default='text'),
        sa.Column('tokens_input', sa.Integer, server_default='0'),
        sa.Column('tokens_output', sa.Integer, server_default='0'),
        sa.Column('model_used', sa.String(100)),
        sa.Column('confidence_score', sa.Float),
        sa.Column('processing_time_ms', sa.Integer),
        sa.Column('external_message_id', sa.String(255)),
        sa.Column('delivery_status', sa.String(50)),
        sa.Column('intent', sa.String(100)),
        sa.Column('sentiment', sa.String(50)),
        sa.Column('entities', postgresql.JSON),
        sa.Column('metadata', postgresql.JSON, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_index('ix_messages_created_at', 'messages', ['created_at'])

    # Knowledge Bases table
    op.create_table(
        'knowledge_bases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('category', sa.String(100), server_default='general'),
        sa.Column('source_type', sa.String(50), server_default='document'),
        sa.Column('source_url', sa.String(500)),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('chunk_count', sa.Integer, server_default='0'),
        sa.Column('last_synced_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_knowledge_bases_client_id', 'knowledge_bases', ['client_id'])

    # Knowledge Chunks table
    op.create_table(
        'knowledge_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('knowledge_base_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('knowledge_bases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('token_count', sa.Integer, nullable=False),
        sa.Column('chunk_index', sa.Integer, nullable=False),
        sa.Column('metadata', postgresql.JSON, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_knowledge_chunks_knowledge_base_id', 'knowledge_chunks', ['knowledge_base_id'])
    op.create_index('ix_knowledge_chunks_client_id', 'knowledge_chunks', ['client_id'])

    # Qualification Rules table
    op.create_table(
        'qualification_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('category', sa.String(100), server_default='qualification'),
        sa.Column('priority', sa.Integer, server_default='0'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('field', sa.String(100), nullable=False),
        sa.Column('operator', sa.String(50), nullable=False),
        sa.Column('value', sa.Text, nullable=False),
        sa.Column('score_impact', sa.Integer, server_default='0'),
        sa.Column('result_score', sa.String(50)),
        sa.Column('result_action', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_qualification_rules_client_id', 'qualification_rules', ['client_id'])

    # Escalations table
    op.create_table(
        'escalations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('leads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reason', sa.String(100), nullable=False),
        sa.Column('reason_details', sa.Text),
        sa.Column('priority', sa.String(50), server_default='normal'),
        sa.Column('status', sa.String(50), server_default='pending'),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
        sa.Column('resolved_by', sa.String(255)),
        sa.Column('resolution_notes', sa.Text),
        sa.Column('notification_sent_at', sa.DateTime(timezone=True)),
        sa.Column('notification_channels', postgresql.ARRAY(sa.String)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_escalations_client_id', 'escalations', ['client_id'])
    op.create_index('ix_escalations_status', 'escalations', ['status'])

    # Usage Logs table
    op.create_table(
        'usage_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('operation', sa.String(100), nullable=False),
        sa.Column('tokens_input', sa.Integer, nullable=False),
        sa.Column('tokens_output', sa.Integer, nullable=False),
        sa.Column('tokens_total', sa.Integer, nullable=False),
        sa.Column('cost_microdollars', sa.Integer, server_default='0'),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True)),
        sa.Column('message_id', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_usage_logs_client_id', 'usage_logs', ['client_id'])
    op.create_index('ix_usage_logs_created_at', 'usage_logs', ['created_at'])

    # Audit Logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='SET NULL')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=False),
        sa.Column('resource_id', sa.String(255)),
        sa.Column('old_values', sa.Text),
        sa.Column('new_values', sa.Text),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('request_id', sa.String(100)),
        sa.Column('description', sa.Text),
        sa.Column('severity', sa.String(20), server_default='info'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_audit_logs_client_id', 'audit_logs', ['client_id'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])

    # Rate Limit Records table
    op.create_table(
        'rate_limit_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key', sa.String(255), nullable=False),
        sa.Column('request_count', sa.Integer, server_default='1'),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('window_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('blocked_until', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_rate_limit_key', 'rate_limit_records', ['key'])


def downgrade() -> None:
    op.drop_table('rate_limit_records')
    op.drop_table('audit_logs')
    op.drop_table('usage_logs')
    op.drop_table('escalations')
    op.drop_table('qualification_rules')
    op.drop_table('knowledge_chunks')
    op.drop_table('knowledge_bases')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('leads')
    op.drop_table('user_sessions')
    op.drop_table('users')
    op.drop_table('clients')
