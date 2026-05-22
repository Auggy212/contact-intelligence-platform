"""add_fk_constraints

Revision ID: dd7e3d60e666
Revises: 0001
Create Date: 2026-05-18 18:58:18.089319

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'dd7e3d60e666'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing FK constraints and indexes
    op.create_foreign_key('fk_analysis_tasks_project_id', 'analysis_tasks', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('fk_audit_log_organization_id', 'audit_log', 'organizations', ['organization_id'], ['id'])
    op.create_foreign_key('fk_checklist_rules_organization_id', 'checklist_rules', 'organizations', ['organization_id'], ['id'])

    op.create_index(op.f('ix_clause_flags_clause_id'), 'clause_flags', ['clause_id'], unique=False)
    op.create_index(op.f('ix_clause_flags_task_id'), 'clause_flags', ['task_id'], unique=False)
    op.create_foreign_key('fk_clause_flags_task_id', 'clause_flags', 'analysis_tasks', ['task_id'], ['id'])
    op.create_foreign_key('fk_clause_flags_clause_id', 'clause_flags', 'parsed_clauses', ['clause_id'], ['id'])
    op.create_foreign_key('fk_clause_library_entries_organization_id', 'clause_library_entries', 'organizations', ['organization_id'], ['id'])

    op.create_index(op.f('ix_memberships_organization_id'), 'memberships', ['organization_id'], unique=False)
    op.create_index(op.f('ix_memberships_user_id'), 'memberships', ['user_id'], unique=False)
    op.create_foreign_key('fk_memberships_user_id', 'memberships', 'users', ['user_id'], ['id'])
    op.create_foreign_key('fk_memberships_organization_id', 'memberships', 'organizations', ['organization_id'], ['id'])

    op.create_foreign_key('fk_parsed_clauses_file_id', 'parsed_clauses', 'project_files', ['file_id'], ['id'])

    op.create_index(op.f('ix_projects_workspace_id'), 'projects', ['workspace_id'], unique=False)
    op.create_foreign_key('fk_projects_organization_id', 'projects', 'organizations', ['organization_id'], ['id'])
    op.create_foreign_key('fk_projects_workspace_id', 'projects', 'workspaces', ['workspace_id'], ['id'])

    op.create_foreign_key('fk_project_files_project_id', 'project_files', 'projects', ['project_id'], ['id'])

    op.create_index(op.f('ix_subscriptions_organization_id'), 'subscriptions', ['organization_id'], unique=True)
    op.create_foreign_key('fk_subscriptions_organization_id', 'subscriptions', 'organizations', ['organization_id'], ['id'])

    op.create_index(op.f('ix_task_results_organization_id'), 'task_results', ['organization_id'], unique=False)
    op.create_index(op.f('ix_task_results_task_id'), 'task_results', ['task_id'], unique=True)
    op.create_foreign_key('fk_task_results_task_id', 'task_results', 'analysis_tasks', ['task_id'], ['id'])

    op.create_index(op.f('ix_usage_records_organization_id'), 'usage_records', ['organization_id'], unique=False)
    op.create_index(op.f('ix_usage_records_subscription_id'), 'usage_records', ['subscription_id'], unique=False)
    op.create_foreign_key('fk_usage_records_subscription_id', 'usage_records', 'subscriptions', ['subscription_id'], ['id'])

    op.create_foreign_key('fk_workspaces_organization_id', 'workspaces', 'organizations', ['organization_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_workspaces_organization_id', 'workspaces', type_='foreignkey')
    op.drop_index(op.f('ix_usage_records_subscription_id'), table_name='usage_records')
    op.drop_index(op.f('ix_usage_records_organization_id'), table_name='usage_records')
    op.drop_constraint('fk_usage_records_subscription_id', 'usage_records', type_='foreignkey')
    op.drop_index(op.f('ix_task_results_task_id'), table_name='task_results')
    op.drop_index(op.f('ix_task_results_organization_id'), table_name='task_results')
    op.drop_constraint('fk_task_results_task_id', 'task_results', type_='foreignkey')
    op.drop_constraint('fk_subscriptions_organization_id', 'subscriptions', type_='foreignkey')
    op.drop_index(op.f('ix_subscriptions_organization_id'), table_name='subscriptions')
    op.drop_constraint('fk_project_files_project_id', 'project_files', type_='foreignkey')
    op.drop_constraint('fk_projects_workspace_id', 'projects', type_='foreignkey')
    op.drop_constraint('fk_projects_organization_id', 'projects', type_='foreignkey')
    op.drop_index(op.f('ix_projects_workspace_id'), table_name='projects')
    op.drop_constraint('fk_parsed_clauses_file_id', 'parsed_clauses', type_='foreignkey')
    op.drop_constraint('fk_memberships_organization_id', 'memberships', type_='foreignkey')
    op.drop_constraint('fk_memberships_user_id', 'memberships', type_='foreignkey')
    op.drop_index(op.f('ix_memberships_user_id'), table_name='memberships')
    op.drop_index(op.f('ix_memberships_organization_id'), table_name='memberships')
    op.drop_constraint('fk_clause_library_entries_organization_id', 'clause_library_entries', type_='foreignkey')
    op.drop_constraint('fk_clause_flags_clause_id', 'clause_flags', type_='foreignkey')
    op.drop_constraint('fk_clause_flags_task_id', 'clause_flags', type_='foreignkey')
    op.drop_index(op.f('ix_clause_flags_task_id'), table_name='clause_flags')
    op.drop_index(op.f('ix_clause_flags_clause_id'), table_name='clause_flags')
    op.drop_constraint('fk_checklist_rules_organization_id', 'checklist_rules', type_='foreignkey')
    op.drop_constraint('fk_audit_log_organization_id', 'audit_log', type_='foreignkey')
    op.drop_constraint('fk_analysis_tasks_project_id', 'analysis_tasks', type_='foreignkey')
