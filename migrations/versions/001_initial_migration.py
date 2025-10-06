"""
Initial database migration - SQLite to PostgreSQL
File: migrations/versions/001_initial_migration.py

Revision ID: 001_initial
Create Date: 2025-10-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables with PostgreSQL-optimized types"""
    
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='pharmacist'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create index on email for faster lookups
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_role', 'users', ['role'])
    
    # Prescriptions table
    op.create_table(
        'prescriptions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), 
                  nullable=False, index=True),
        sa.Column('patient_name', sa.String(length=200), nullable=True),
        sa.Column('patient_id', sa.String(length=100), nullable=True, index=True),
        sa.Column('doctor_name', sa.String(length=200), nullable=True),
        sa.Column('doctor_license', sa.String(length=100), nullable=True),
        sa.Column('prescription_date', sa.Date(), nullable=True),
        sa.Column('input_format', sa.String(length=50), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, 
                  server_default='pending', index=True),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create composite indexes for common queries
    op.create_index('idx_prescriptions_user_status', 'prescriptions', 
                    ['user_id', 'status'])
    op.create_index('idx_prescriptions_created', 'prescriptions', 
                    ['created_at'])
    
    # Medications table
    op.create_table(
        'medications',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('prescription_id', sa.Integer(), 
                  sa.ForeignKey('prescriptions.id', ondelete='CASCADE'), 
                  nullable=False, index=True),
        sa.Column('drug_name', sa.String(length=200), nullable=False, index=True),
        sa.Column('dosage', sa.String(length=100), nullable=True),
        sa.Column('frequency', sa.String(length=100), nullable=True),
        sa.Column('duration', sa.String(length=100), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('refills', sa.Integer(), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    op.create_index('idx_medications_prescription', 'medications', 
                    ['prescription_id'])
    
    # Validation results table
    op.create_table(
        'validation_results',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('prescription_id', sa.Integer(), 
                  sa.ForeignKey('prescriptions.id', ondelete='CASCADE'), 
                  nullable=False, index=True),
        sa.Column('validation_type', sa.String(length=100), nullable=False, index=True),
        sa.Column('severity', sa.String(length=50), nullable=False, index=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', postgresql.JSONB(), nullable=True),  # PostgreSQL JSONB for efficient querying
        sa.Column('is_resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('resolved_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), 
                  nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    op.create_index('idx_validation_results_prescription', 'validation_results', 
                    ['prescription_id'])
    op.create_index('idx_validation_results_severity', 'validation_results', 
                    ['severity', 'is_resolved'])
    
    # Audit logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), 
                  nullable=True, index=True),
        sa.Column('prescription_id', sa.Integer(), 
                  sa.ForeignKey('prescriptions.id', ondelete='CASCADE'), 
                  nullable=True, index=True),
        sa.Column('action', sa.String(length=100), nullable=False, index=True),
        sa.Column('entity_type', sa.String(length=50), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('old_values', postgresql.JSONB(), nullable=True),
        sa.Column('new_values', postgresql.JSONB(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP'), index=True),
    )
    
    # Composite index for audit queries
    op.create_index('idx_audit_logs_user_action', 'audit_logs', 
                    ['user_id', 'action', 'created_at'])
    
    # Create trigger function for updated_at timestamps (PostgreSQL specific)
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Apply triggers to tables with updated_at columns
    for table in ['users', 'prescriptions', 'medications', 'validation_results']:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at 
            BEFORE UPDATE ON {table}
            FOR EACH ROW 
            EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    """Drop all tables and triggers"""
    
    # Drop triggers first
    for table in ['users', 'prescriptions', 'medications', 'validation_results']:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};")
    
    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
    
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('audit_logs')
    op.drop_table('validation_results')
    op.drop_table('medications')
    op.drop_table('prescriptions')
    op.drop_table('users')
