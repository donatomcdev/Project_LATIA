from alembic import context

from latia.config import database_engine
from latia.models import Base, SCHEMA


with database_engine("MIGRATION_DATABASE_URL").connect() as connection:
    # The version table belongs in the same private schema as the app tables.
    with connection.begin():
        # Keep LATIA explicit even when the database role is also named latia.
        connection.exec_driver_sql("SET search_path TO pg_catalog")
        connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS latia")
    connection.dialect.default_schema_name = "pg_catalog"

    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        version_table_schema=SCHEMA,
        include_schemas=True,
        include_name=lambda name, kind, parents: kind != "schema" or name == SCHEMA,
    )
    with context.begin_transaction():
        context.run_migrations()
