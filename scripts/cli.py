import click
from flask import current_app
from werkzeug.security import generate_password_hash
from models import db
from models.user import User
import getpass


def register_cli(app):

    @app.cli.command("create-user")
    @click.argument("username")
    @click.option("--admin", is_flag=True, help="Create as admin user")
    def create_user_command(username, admin):
        """Create a new user with a hashed password."""

        password = getpass.getpass("Enter password: ")
        confirm = getpass.getpass("Confirm password: ")

        if password != confirm:
            click.echo("❌ Passwords do not match.")
            return

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            click.echo(f"⚠️ User '{username}' already exists.")
            return

        user = User(
            username=username,
            role="admin" if admin else "user",
        )

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        click.echo(f"✅ User '{username}' created successfully.")

    @app.cli.command("backup-db")
    def backup_db_command():
        """Upload a backup of the SQLite database to Azure now."""

        db_backup = current_app.extensions.get("db_backup")
        if not db_backup:
            click.echo("❌ Azure storage is not configured.")
            return

        blob_name = db_backup.backup()
        if blob_name:
            click.echo(f"✅ Backed up to '{blob_name}'.")
        else:
            click.echo("⚠️ No database file to back up.")
