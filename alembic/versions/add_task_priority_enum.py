"""add task priority enum

Revision ID: add_task_priority_enum
Revises: 598d0a354503
Create Date: 2024-01-01 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_task_priority_enum"
down_revision = "598d0a354503"
branch_labels = None
depends_on = None


def upgrade():
    # Create the new enum type
    task_priority_enum = postgresql.ENUM(
        "low", "medium", "high", "urgent", name="task_priority"
    )
    task_priority_enum.create(op.get_bind())

    # Add the new priority column with the enum type
    op.add_column("tasks", sa.Column("priority_new", task_priority_enum, nullable=True))

    # Convert existing integer priority values to enum values
    # Cast the text values to the enum type
    op.execute("""
        UPDATE tasks
        SET priority_new = CASE
            WHEN priority <= 2 THEN 'low'::task_priority
            WHEN priority = 3 THEN 'medium'::task_priority
            WHEN priority = 4 THEN 'high'::task_priority
            WHEN priority >= 5 THEN 'urgent'::task_priority
            ELSE 'medium'::task_priority
        END
    """)

    # Set default value for any NULL priorities
    op.execute(
        "UPDATE tasks SET priority_new = 'medium'::task_priority WHERE priority_new IS NULL"
    )

    # Make the new column not nullable
    op.alter_column("tasks", "priority_new", nullable=False)

    # Drop the old priority column
    op.drop_column("tasks", "priority")

    # Rename the new column to priority
    op.alter_column("tasks", "priority_new", new_column_name="priority")

    # Create indexes for the new priority column
    # Note: ix_tasks_priority is now handled automatically by the model column definition
    op.create_index("ix_tasks_owner_priority", "tasks", ["owner_id", "priority"])


def downgrade():
    # Drop the new indexes
    op.drop_index("ix_tasks_owner_priority", "tasks")
    # Note: ix_tasks_priority is handled automatically by the model, no need to drop it

    # Add back the old integer priority column
    op.add_column(
        "tasks", sa.Column("priority", sa.Integer(), nullable=False, server_default="3")
    )

    # Convert enum values back to integers
    op.execute("""
        UPDATE tasks
        SET priority = CASE
            WHEN priority = 'low' THEN 2
            WHEN priority = 'medium' THEN 3
            WHEN priority = 'high' THEN 4
            WHEN priority = 'urgent' THEN 5
            ELSE 3
        END
    """)

    # Drop the enum type
    task_priority_enum = postgresql.ENUM(
        "low", "medium", "high", "urgent", name="task_priority"
    )
    task_priority_enum.drop(op.get_bind())
