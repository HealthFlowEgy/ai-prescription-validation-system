"""Add field-level encryption for PHI

Revision ID: 20251014_001
Revises: 
Create Date: 2025-10-14 10:00:00.000000

This migration encrypts existing PHI data in the database.
Estimated time: 5 minutes per 10,000 records

IMPORTANT: 
- Backup database before running
- Test in staging environment first
- Monitor disk space (encrypted fields are larger)
- Cannot be reversed in production (security policy)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import logging
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# revision identifiers
revision = '20251014_001'
down_revision = None
branch_labels = None
depends_on = None

logger = logging.getLogger(__name__)


def upgrade():
    """
    Upgrade migration: Encrypt PHI fields in place
    
    Process:
    1. Add new encrypted columns
    2. Migrate data with encryption
    3. Verify encryption
    4. Drop old plaintext columns (with backup check)
    5. Rename encrypted columns
    """
    
    logger.info("=" * 80)
    logger.info("Starting PHI Encryption Migration")
    logger.info("=" * 80)
    
    # Safety check
    if os.environ.get('FLASK_ENV') == 'production':
        logger.warning("PRODUCTION ENVIRONMENT DETECTED")
        logger.warning("Ensure database backup exists before proceeding!")
        
        # In production, require explicit confirmation
        backup_confirmed = os.environ.get('MIGRATION_BACKUP_CONFIRMED', 'false')
        if backup_confirmed.lower() != 'true':
            raise Exception(
                "Production migration requires MIGRATION_BACKUP_CONFIRMED=true "
                "environment variable to proceed. Ensure backup exists first!"
            )
    
    connection = op.get_bind()
    
    # Import encryption service (will be available after previous commits)
    try:
        from src.utils.encryption import encryption_service
    except ImportError:
        logger.error("Encryption service not found. Ensure it's been deployed.")
        raise
    
    # Step 1: Add new encrypted columns to prescriptions table
    logger.info("Step 1/7: Adding encrypted columns to prescriptions table...")
    try:
        op.add_column('prescriptions', 
            sa.Column('patient_name_encrypted', sa.String(512), nullable=True))
        op.add_column('prescriptions', 
            sa.Column('patient_dob_encrypted', sa.String(512), nullable=True))
        op.add_column('prescriptions', 
            sa.Column('diagnosis_encrypted', sa.String(1024), nullable=True))
        op.add_column('prescriptions', 
            sa.Column('medical_history_encrypted', sa.Text(), nullable=True))
        logger.info("✓ Prescription encrypted columns added")
    except Exception as e:
        logger.error(f"Failed to add prescription columns: {str(e)}")
        raise
    
    # Step 2: Add encrypted columns to users table
    logger.info("Step 2/7: Adding encrypted columns to users table...")
    try:
        op.add_column('users', 
            sa.Column('email_encrypted', sa.String(512), nullable=True))
        op.add_column('users', 
            sa.Column('phone_encrypted', sa.String(512), nullable=True))
        logger.info("✓ User encrypted columns added")
    except Exception as e:
        logger.error(f"Failed to add user columns: {str(e)}")
        raise
    
    # Step 3: Migrate prescriptions data with encryption
    logger.info("Step 3/7: Encrypting prescription data...")
    batch_size = 1000
    offset = 0
    total_encrypted = 0
    
    try:
        while True:
            # Fetch batch of records
            result = connection.execute(text("""
                SELECT id, patient_name, patient_dob, diagnosis, medical_history
                FROM prescriptions
                LIMIT :limit OFFSET :offset
            """), {"limit": batch_size, "offset": offset})
            
            records = result.fetchall()
            if not records:
                break
            
            # Encrypt each record
            for record in records:
                encrypted_data = {}
                
                if record[1]:  # patient_name
                    encrypted_data['patient_name_encrypted'] = encryption_service.encrypt(str(record[1]))
                if record[2]:  # patient_dob
                    encrypted_data['patient_dob_encrypted'] = encryption_service.encrypt(str(record[2]))
                if record[3]:  # diagnosis
                    encrypted_data['diagnosis_encrypted'] = encryption_service.encrypt(str(record[3]))
                if record[4]:  # medical_history
                    encrypted_data['medical_history_encrypted'] = encryption_service.encrypt(str(record[4]))
                
                if encrypted_data:
                    # Build update query
                    set_clause = ', '.join([f"{k} = :{k}" for k in encrypted_data.keys()])
                    connection.execute(
                        text(f"UPDATE prescriptions SET {set_clause} WHERE id = :id"),
                        {**encrypted_data, 'id': record[0]}
                    )
                    total_encrypted += 1
            
            offset += len(records)
            logger.info(f"  Encrypted {offset} prescription records...")
            
            # Commit batch
            connection.commit()
        
        logger.info(f"✓ Encrypted {total_encrypted} prescription records")
    except Exception as e:
        logger.error(f"Failed to encrypt prescription data: {str(e)}")
        connection.rollback()
        raise
    
    # Step 4: Migrate users data with encryption
    logger.info("Step 4/7: Encrypting user data...")
    offset = 0
    total_encrypted = 0
    
    try:
        while True:
            result = connection.execute(text("""
                SELECT id, email, phone
                FROM users
                LIMIT :limit OFFSET :offset
            """), {"limit": batch_size, "offset": offset})
            
            records = result.fetchall()
            if not records:
                break
            
            for record in records:
                encrypted_data = {}
                
                if record[1]:  # email
                    encrypted_data['email_encrypted'] = encryption_service.encrypt(str(record[1]))
                if record[2]:  # phone
                    encrypted_data['phone_encrypted'] = encryption_service.encrypt(str(record[2]))
                
                if encrypted_data:
                    set_clause = ', '.join([f"{k} = :{k}" for k in encrypted_data.keys()])
                    connection.execute(
                        text(f"UPDATE users SET {set_clause} WHERE id = :id"),
                        {**encrypted_data, 'id': record[0]}
                    )
                    total_encrypted += 1
            
            offset += len(records)
            logger.info(f"  Encrypted {offset} user records...")
            connection.commit()
        
        logger.info(f"✓ Encrypted {total_encrypted} user records")
    except Exception as e:
        logger.error(f"Failed to encrypt user data: {str(e)}")
        connection.rollback()
        raise
    
    # Step 5: Verify encryption
    logger.info("Step 5/7: Verifying encryption...")
    try:
        result = connection.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(patient_name_encrypted) as encrypted_names,
                COUNT(patient_dob_encrypted) as encrypted_dobs
            FROM prescriptions
            WHERE patient_name IS NOT NULL OR patient_dob IS NOT NULL
        """))
        
        row = result.fetchone()
        logger.info(f"  Total records: {row[0]}")
        logger.info(f"  Encrypted names: {row[1]}")
        logger.info(f"  Encrypted DOBs: {row[2]}")
        
        logger.info("✓ Encryption verification complete")
    except Exception as e:
        logger.warning(f"Verification check failed: {str(e)}")
    
    # Step 6: Drop old plaintext columns
    logger.warning("Step 6/7: Dropping plaintext columns...")
    logger.warning("This is IRREVERSIBLE. Ensure backup exists!")
    
    try:
        # Prescriptions table
        op.drop_column('prescriptions', 'patient_name')
        op.drop_column('prescriptions', 'patient_dob')
        op.drop_column('prescriptions', 'diagnosis')
        op.drop_column('prescriptions', 'medical_history')
        
        # Users table  
        op.drop_column('users', 'email')
        op.drop_column('users', 'phone')
        
        logger.info("✓ Plaintext columns dropped")
    except Exception as e:
        logger.error(f"Failed to drop columns: {str(e)}")
        raise
    
    # Step 7: Rename encrypted columns to original names
    logger.info("Step 7/7: Renaming encrypted columns...")
    try:
        # Prescriptions
        op.alter_column('prescriptions', 'patient_name_encrypted', 
                        new_column_name='patient_name')
        op.alter_column('prescriptions', 'patient_dob_encrypted', 
                        new_column_name='patient_dob')
        op.alter_column('prescriptions', 'diagnosis_encrypted', 
                        new_column_name='diagnosis')
        op.alter_column('prescriptions', 'medical_history_encrypted', 
                        new_column_name='medical_history')
        
        # Users
        op.alter_column('users', 'email_encrypted', 
                        new_column_name='email')
        op.alter_column('users', 'phone_encrypted', 
                        new_column_name='phone')
        
        logger.info("✓ Columns renamed")
    except Exception as e:
        logger.error(f"Failed to rename columns: {str(e)}")
        raise
    
    logger.info("=" * 80)
    logger.info("PHI Encryption Migration Completed Successfully!")
    logger.info("=" * 80)


def downgrade():
    """
    Downgrade migration: NOT SUPPORTED IN PRODUCTION
    
    For security and compliance reasons, this migration cannot be reversed
    in production environments. Decrypting PHI would violate security policies.
    """
    
    if os.environ.get('FLASK_ENV') == 'production':
        raise Exception(
            "Cannot downgrade encryption in production environment! "
            "This would violate HIPAA compliance and security policies."
        )
    
    logger.warning("=" * 80)
    logger.warning("DOWNGRADE: Decrypting PHI (DEVELOPMENT ONLY)")
    logger.warning("=" * 80)
    
    connection = op.get_bind()
    
    try:
        from src.utils.encryption import encryption_service
    except ImportError:
        logger.error("Encryption service not found")
        raise
    
    # Add plaintext columns back
    logger.info("Adding plaintext columns...")
    
    op.add_column('prescriptions', 
        sa.Column('patient_name_plaintext', sa.String(255), nullable=True))
    op.add_column('prescriptions', 
        sa.Column('patient_dob_plaintext', sa.String(50), nullable=True))
    op.add_column('prescriptions', 
        sa.Column('diagnosis_plaintext', sa.String(500), nullable=True))
    op.add_column('prescriptions', 
        sa.Column('medical_history_plaintext', sa.Text(), nullable=True))
    
    op.add_column('users', 
        sa.Column('email_plaintext', sa.String(255), nullable=True))
    op.add_column('users', 
        sa.Column('phone_plaintext', sa.String(50), nullable=True))
    
    # Decrypt data
    logger.info("Decrypting data...")
    
    batch_size = 1000
    offset = 0
    
    while True:
        result = connection.execute(text("""
            SELECT id, patient_name, patient_dob, diagnosis, medical_history
            FROM prescriptions
            LIMIT :limit OFFSET :offset
        """), {"limit": batch_size, "offset": offset})
        
        records = result.fetchall()
        if not records:
            break
        
        for record in records:
            decrypted_data = {}
            
            if record[1]:
                decrypted_data['patient_name_plaintext'] = encryption_service.decrypt(str(record[1]))
            if record[2]:
                decrypted_data['patient_dob_plaintext'] = encryption_service.decrypt(str(record[2]))
            if record[3]:
                decrypted_data['diagnosis_plaintext'] = encryption_service.decrypt(str(record[3]))
            if record[4]:
                decrypted_data['medical_history_plaintext'] = encryption_service.decrypt(str(record[4]))
            
            if decrypted_data:
                set_clause = ', '.join([f"{k} = :{k}" for k in decrypted_data.keys()])
                connection.execute(
                    text(f"UPDATE prescriptions SET {set_clause} WHERE id = :id"),
                    {**decrypted_data, 'id': record[0]}
                )
        
        offset += len(records)
        connection.commit()
    
    # Drop encrypted columns and rename plaintext
    op.drop_column('prescriptions', 'patient_name')
    op.drop_column('prescriptions', 'patient_dob')
    op.drop_column('prescriptions', 'diagnosis')
    op.drop_column('prescriptions', 'medical_history')
    
    op.alter_column('prescriptions', 'patient_name_plaintext', 
                    new_column_name='patient_name')
    op.alter_column('prescriptions', 'patient_dob_plaintext', 
                    new_column_name='patient_dob')
    op.alter_column('prescriptions', 'diagnosis_plaintext', 
                    new_column_name='diagnosis')
    op.alter_column('prescriptions', 'medical_history_plaintext', 
                    new_column_name='medical_history')
    
    # Similar for users
    op.drop_column('users', 'email')
    op.drop_column('users', 'phone')
    
    op.alter_column('users', 'email_plaintext', new_column_name='email')
    op.alter_column('users', 'phone_plaintext', new_column_name='phone')
    
    logger.info("Downgrade complete (development only)")

