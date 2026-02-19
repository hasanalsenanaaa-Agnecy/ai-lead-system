"""Reset admin password to a known value for testing."""
import asyncio
import sys
sys.path.insert(0, ".")

from app.db.session import get_db_context
from app.core.auth import hash_password
from sqlalchemy import text


async def reset_password():
    email = "admin@sunsetdental.com"
    new_password = "Admin123!@#"

    async with get_db_context() as db:
        new_hash = hash_password(new_password)
        result = await db.execute(
            text("UPDATE users SET password_hash = :ph WHERE email = :email"),
            {"ph": new_hash, "email": email},
        )
        await db.commit()
        print(f"Password reset for {email}")
        print(f"New password: {new_password}")
        print(f"Rows updated: {result.rowcount}")


if __name__ == "__main__":
    asyncio.run(reset_password())
