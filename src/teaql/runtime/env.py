import os
from .context import UserContext
from teaql.provider.sqlite import create_sqlite_service

class ServiceRuntimeFromEnv:
    @staticmethod
    def build_context() -> UserContext:
        ctx = UserContext.new()
        # Initialize context based on common teaql environment variables
        env_user = os.environ.get("TEAQL_USER", "")
        if env_user:
            ctx.set_user_identifier(env_user)
            
        db_url = os.environ.get("TEAQL_DB_URL") or os.environ.get("DATABASE_URL")
        if db_url:
            if db_url.startswith("sqlite://"):
                data_service = create_sqlite_service(db_url)
                ctx.insert_resource("dataService", data_service)
        
        return ctx
