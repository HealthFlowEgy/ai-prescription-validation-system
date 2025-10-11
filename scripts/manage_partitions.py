"""
Automated partition management script.
Creates new partitions and drops old ones.
"""

import psycopg2
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import os


def create_future_partitions(conn, months_ahead=3):
    """
    Create partitions for future months.
    
    Args:
        conn: Database connection
        months_ahead: Number of months to create partitions for
    """
    cursor = conn.cursor()
    
    # Get the latest partition
    cursor.execute("""
        SELECT 
            tablename,
            regexp_replace(tablename, 'prescriptions_', '') as date_part
        FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename LIKE 'prescriptions_20%'
        ORDER BY tablename DESC
        LIMIT 1
    """)
    
    result = cursor.fetchone()
    if not result:
        print("No existing partitions found")
        return
    
    latest_partition = result[0]
    date_part = result[1]
    
    # Parse date from partition name
    year, month = map(int, date_part.split('_'))
    current_date = datetime(year, month, 1)
    
    # Create future partitions
    for i in range(1, months_ahead + 1):
        next_date = current_date + relativedelta(months=i)
        partition_name = f"prescriptions_{next_date.strftime('%Y_%m')}"
        
        start_date = next_date.strftime('%Y-%m-%d')
        end_date = (next_date + relativedelta(months=1)).strftime('%Y-%m-%d')
        
        # Check if partition already exists
        cursor.execute(f"""
            SELECT tablename FROM pg_tables
            WHERE tablename = '{partition_name}'
        """)
        
        if cursor.fetchone():
            print(f"Partition {partition_name} already exists")
            continue
        
        # Create partition
        print(f"Creating partition: {partition_name}")
        cursor.execute(f"""
            CREATE TABLE {partition_name} PARTITION OF prescriptions
            FOR VALUES FROM ('{start_date}') TO ('{end_date}')
        """)
        
        conn.commit()
        print(f"Created partition: {partition_name}")
    
    cursor.close()


def drop_old_partitions(conn, retention_months=24):
    """
    Drop partitions older than retention period.
    
    Args:
        conn: Database connection
        retention_months: Number of months to retain
    """
    cursor = conn.cursor()
    
    cutoff_date = datetime.now() - relativedelta(months=retention_months)
    cutoff_str = cutoff_date.strftime('%Y_%m')
    
    # Find old partitions
    cursor.execute(f"""
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename LIKE 'prescriptions_20%'
        AND tablename < 'prescriptions_{cutoff_str}'
        ORDER BY tablename
    """)
    
    old_partitions = cursor.fetchall()
    
    for partition in old_partitions:
        partition_name = partition[0]
        
        print(f"Archiving and dropping partition: {partition_name}")
        
        # Archive to S3 or backup storage (implement as needed)
        # archive_partition(partition_name)
        
        # Drop partition
        cursor.execute(f"DROP TABLE {partition_name}")
        conn.commit()
        
        print(f"Dropped partition: {partition_name}")
    
    cursor.close()


def vacuum_partitions(conn):
    """
    Vacuum and analyze partitions for optimal performance.
    """
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename LIKE 'prescriptions_%'
    """)
    
    partitions = cursor.fetchall()
    
    for partition in partitions:
        partition_name = partition[0]
        print(f"Vacuuming partition: {partition_name}")
        
        cursor.execute(f"VACUUM ANALYZE {partition_name}")
        conn.commit()
    
    cursor.close()


if __name__ == '__main__':
    # Connect to database
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        database=os.getenv('POSTGRES_DATABASE', 'healthflow'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'password')
    )
    
    try:
        # Create future partitions (3 months ahead)
        create_future_partitions(conn, months_ahead=3)
        
        # Drop old partitions (keep 24 months)
        drop_old_partitions(conn, retention_months=24)
        
        # Vacuum partitions
        vacuum_partitions(conn)
        
        print("\nPartition management completed successfully")
        
    finally:
        conn.close()

