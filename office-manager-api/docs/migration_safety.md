# Database Migration Safety Guidelines

This document outlines best practices for writing safe database migrations that minimize risk and ensure rollback capability.

## Golden Rules

1. **Always be backward-compatible**
2. **Add new columns as nullable first**
3. **Backfill data in a separate step**
4. **Make columns required after backfill**
5. **Test migrations on staging before production**

## Migration Template

```python
"""
Migration: Add new column example

Safety: Safe - adds nullable column with default
Rollback: Simple column drop
"""
from alembic import op
import sqlalchemy as sa

# Revision ID and dependencies
revision = 'abc123'
down_revision = 'xyz789'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Add column as nullable (no default initially)
    op.add_column(
        'users',
        sa.Column('new_field', sa.String(255), nullable=True)
    )
    
    # Step 2: Backfill existing rows (if needed)
    # Use raw SQL for performance on large tables
    op.execute(
        "UPDATE users SET new_field = 'default_value' WHERE new_field IS NULL"
    )
    
    # Step 3: Add NOT NULL constraint (if needed)
    # Only after confirming all rows have values
    # op.alter_column('users', 'new_field', nullable=False)
    
    # Alternative: Add column with default (safer for zero-downtime)
    # op.add_column(
    #     'users',
    #     sa.Column('new_field', sa.String(255), server_default='default_value', nullable=True)
    # )


def downgrade():
    # Always reverse the changes
    op.drop_column('users', 'new_field')
```

## Safe Patterns

### Adding a New Table

```python
def upgrade():
    # Create table with all constraints needed
    op.create_table(
        'new_table',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime()),
    )
    
    # Add indexes
    op.create_index('ix_new_table_tenant_id', 'new_table', ['tenant_id'])

def downgrade():
    op.drop_index('ix_new_table_tenant_id')
    op.drop_table('new_table')
```

### Adding a Non-Nullable Column with Default

```python
def upgrade():
    # Add column with server default
    op.add_column(
        'tasks',
        sa.Column(
            'priority',
            sa.String(20),
            server_default='medium',
            nullable=True
        )
    )

def downgrade():
    op.drop_column('tasks', 'priority')
```

### Renaming a Column (Safely)

```python
def upgrade():
    # Step 1: Add new column
    op.add_column('users', sa.Column('full_name', sa.String(255)))
    
    # Step 2: Copy data
    op.execute("UPDATE users SET full_name = name")
    
    # Step 3: Update application code to use new column
    # Deploy new code
    
    # Step 4: Drop old column (in next migration)
    # op.drop_column('users', 'name')

def downgrade():
    # Reverse the process
    op.add_column('users', sa.Column('name', sa.String(255)))
    op.execute("UPDATE users SET name = full_name")
    op.drop_column('users', 'full_name')
```

### Adding an Index

```python
def upgrade():
    # CONCURRENTLY is crucial for zero-downtime on large tables
    op.execute(
        "CREATE INDEX CONCURRENTLY ix_tasks_tenant_created "
        "ON tasks (tenant_id, created_at DESC)"
    )

def downgrade():
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_tasks_tenant_created")
```

### Adding a Foreign Key

```python
def upgrade():
    # Add FK as NOT VALID initially
    op.execute(
        "ALTER TABLE tasks "
        "ADD CONSTRAINT fk_tasks_assignee "
        "REFERENCES users(id) NOT VALID"
    )
    
    # Validate in a separate maintenance window
    # op.execute("ALTER TABLE tasks VALIDATE CONSTRAINT fk_tasks_assignee")

def downgrade():
    op.execute("ALTER TABLE tasks DROP CONSTRAINT IF EXISTS fk_tasks_assignee")
```

## Dangerous Patterns to Avoid

### ❌ Never Do This

```python
# BAD: Dropping a column with data loss
def downgrade():
    op.drop_column('users', 'important_data')

# BAD: Renaming without backup plan
op.rename_column('users', 'old_name', 'new_name')

# BAD: Changing type without proper casting
op.alter_column('users', 'age', type_=sa.BigInteger())

# BAD: Adding NOT NULL without backfill
op.add_column('users', sa.Column('required_field', sa.String(255), nullable=False))
```

## Migration Checklist

Before deploying to production:

- [ ] Migration tested on staging with production-like data volume
- [ ] Rollback migration written and tested
- [ ] Estimated downtime calculated
- [ ] Backups taken before migration
- [ ] Monitoring alerts prepared
- [ ] Rollback plan communicated to team
- [ ] Estimated time for migration documented

## Large Table Considerations

For tables with millions of rows:

```python
def upgrade():
    # Use batch operations for large data changes
    from sqlalchemy.dialects.postgresql import insert
    
    # Chunk the backfill
    batch_size = 10000
    offset = 0
    
    while True:
        result = op.execute(
            sa.text(f"""
                SELECT id FROM users 
                WHERE new_field IS NULL 
                LIMIT {batch_size}
            """)
        )
        
        if result.rowcount == 0:
            break
        
        ids = [row[0] for row in result]
        
        op.execute(
            sa.text(f"""
                UPDATE users 
                SET new_field = 'default_value' 
                WHERE id = ANY(:ids)
            """),
            {"ids": ids}
        )
        
        offset += batch_size
```

## Zero-Downtime Deployment Strategy

1. **Deploy migration that adds new columns/tables**
2. **Deploy application code that uses new schema**
3. **Run data backfill job (async, no downtime)**
4. **Deploy cleanup migration (remove old columns)**
5. **Verify everything works**

This ensures the database is always in a valid state for the running application code.
