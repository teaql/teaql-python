import os
from .context import UserContext
from teaql.provider.sqlite import create_sqlite_service
from teaql.provider.mysql import create_mysql_service
from teaql.provider.postgres import create_postgres_service

class ServiceRuntimeFromEnv:
    @staticmethod
    def build_context() -> UserContext:
        context = UserContext.new()
        # Initialize context based on common teaql environment variables
        env_user = os.environ.get("TEAQL_USER", "")
        if env_user:
            context.set_user_identifier(env_user)
            
        db_url = os.environ.get("TEAQL_DB_URL") or os.environ.get("DATABASE_URL")
        if db_url:
            data_service = None
            if db_url.startswith("sqlite://") or db_url.startswith("file:"):
                data_service = create_sqlite_service(db_url)
            elif db_url.startswith("mysql://"):
                data_service = create_mysql_service(db_url)
            elif db_url.startswith("postgres://") or db_url.startswith("postgresql://"):
                data_service = create_postgres_service(db_url)
                
            if data_service:
                context.insert_resource("dataService", data_service)
        
        return context
