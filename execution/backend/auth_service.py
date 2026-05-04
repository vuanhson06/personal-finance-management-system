"""
auth_service.py — Authentication & User Management Service
===========================================================
Handles all user-facing identity operations: registration, login validation,
and user retrieval. This module is the exclusive entry point for creating
User records in the system — no other module should insert into the `Users`
table directly.

Security Guarantees:
    - Passwords are NEVER stored or compared in plain text.
    - All hashing is delegated to `User.set_password()` (bcrypt).
    - All verification is delegated to `User.verify_password()` (bcrypt).
    - Email and PhoneNumber uniqueness is validated at the Python layer
      before hitting the DB to produce clean user-facing error messages.
    - On successful registration, the `After_User_Insert` SQL trigger
      fires automatically to seed the new user's Categories.

Directive Reference:
    - directives/backend_logic_rules.md — Section 2 (Registration Flow),
                                          Section 3 (Role-Based Access),
                                          Section 4 (Safe Error Propagation)
    - directives/db_rules.md           — Section 4 (Security Protocols)
"""

import logging
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import User, UserRole

logger = logging.getLogger(__name__)

# =============================================================================
# Validation Helpers
# =============================================================================

_EMAIL_REGEX = re.compile(r"^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z]{2,}$")
_PHONE_REGEX = re.compile(r"^\+?[\d\-\s\(\)]{7,15}$")


def _validate_email(email: str) -> None:
    """
    Validates that an email address matches a standard format.

    Args:
        email: The email string to validate.

    Raises:
        ValueError: If the email does not match the expected pattern.
    """
    if not _EMAIL_REGEX.match(email.strip()):
        raise ValueError(f"Invalid email format: '{email}'.")


def _validate_phone(phone: Optional[str]) -> None:
    """
    Validates that a phone number matches an acceptable format, if provided.
    Phone numbers are optional (nullable) — None is always valid.

    Args:
        phone: The phone number string to validate, or None.

    Raises:
        ValueError: If provided and the format is invalid.
    """
    if phone is not None and not _PHONE_REGEX.match(phone.strip()):
        raise ValueError(
            f"Invalid phone number format: '{phone}'. "
            "Expected format: +1-555-010-1001 or similar."
        )


def _check_email_unique(email: str, db: Session) -> None:
    """
    Queries the DB to confirm that the given email is not already registered.
    Raises a clean ValueError if a duplicate is found, avoiding a raw
    IntegrityError from reaching the UI layer.

    Args:
        email: The email to check.
        db:    An active SQLAlchemy Session.

    Raises:
        ValueError: If the email is already taken.
    """
    existing: Optional[User] = db.execute(
        select(User).where(User.Email == email.strip().lower())
    ).scalar_one_or_none()
    if existing:
        raise ValueError(f"Email '{email}' is already registered.")


def _check_phone_unique(phone: Optional[str], db: Session) -> None:
    """
    Queries the DB to confirm that the given phone number is not already
    associated with another account, if a phone number is provided.

    Args:
        phone: The phone number to check, or None.
        db:    An active SQLAlchemy Session.

    Raises:
        ValueError: If the phone number is already taken.
    """
    if phone is None:
        return
    existing: Optional[User] = db.execute(
        select(User).where(User.PhoneNumber == phone.strip())
    ).scalar_one_or_none()
    if existing:
        raise ValueError(f"Phone number '{phone}' is already registered.")


# =============================================================================
# Step 5.1 — Public Auth Functions
# =============================================================================

def register_user(
    username: str,
    email: str,
    password: str,
    db: Session,
    phone: Optional[str] = None,
    role: UserRole = UserRole.User,
) -> User:
    """
    Registers a new user account in the system.

    Workflow:
        1. Validate email format and phone format (if provided).
        2. Check email and phone uniqueness against the DB.
        3. Create a User ORM object and hash the password via bcrypt.
        4. Commit — the `After_User_Insert` SQL trigger fires automatically,
           calling `InitializeUserCategories` to seed the user's Categories.
        5. Refresh and return the persisted User object.

    Args:
        username: The user's display name (no uniqueness requirement).
        email:    The user's email address. Must be unique. Used for login.
        password: The plain-text password. Will be hashed — never stored raw.
        db:       An active SQLAlchemy Session.
        phone:    Optional phone number. Must be unique if provided.
        role:     The user's role. Defaults to UserRole.User.
                  Only set UserRole.Admin for explicitly administrative accounts.

    Returns:
        The fully persisted User ORM object with a valid UserID.

    Raises:
        ValueError: For format validation failures or uniqueness conflicts.
        RuntimeError: For unexpected DB-level failures (logged internally).
    """
    # --- Pre-ORM Validation ---
    if not username or not username.strip():
        raise ValueError("Username must not be empty.")
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")

    _validate_email(email)
    _validate_phone(phone)
    _check_email_unique(email, db)
    _check_phone_unique(phone, db)

    # --- ORM Insertion ---
    try:
        user = User(
            UserName=username.strip(),
            Email=email.strip().lower(),
            PhoneNumber=phone.strip() if phone else None,
            Role=role,
        )
        user.set_password(password)  # bcrypt hash applied here

        db.add(user)
        db.commit()        # After_User_Insert trigger fires here
        db.refresh(user)

        logger.info(
            "User registered successfully: id=%d email='%s' role=%s.",
            user.UserID, user.Email, user.Role.value,
        )
        return user

    except IntegrityError as e:
        db.rollback()
        logger.error("IntegrityError during registration: %s", e)
        raise RuntimeError(
            "Registration failed due to a database conflict. "
            "Please verify your details and try again."
        ) from e


def login_user(email: str, password: str, db: Session) -> User:
    """
    Authenticates a user by email and password.

    Looks up the user by email, then uses bcrypt to securely verify the
    provided plain-text password against the stored hash. This function
    uses constant-time comparison (via bcrypt) to prevent timing attacks.

    Args:
        email:    The email address of the account to authenticate.
        password: The plain-text password to verify.
        db:       An active SQLAlchemy Session.

    Returns:
        The authenticated User ORM object if credentials are valid.

    Raises:
        ValueError: If the email is not found or the password is incorrect.
                    A single generic message is used to prevent user enumeration.
    """
    _validate_email(email)

    user: Optional[User] = db.execute(
        select(User).where(User.Email == email.strip().lower())
    ).scalar_one_or_none()

    # Use a single generic error to prevent email enumeration attacks
    if user is None or not user.verify_password(password):
        logger.warning("Failed login attempt for email: '%s'.", email)
        raise ValueError("Invalid email or password.")

    logger.info(
        "User logged in: id=%d email='%s' role=%s.",
        user.UserID, user.Email, user.Role.value,
    )
    return user


def get_user_by_id(user_id: int, db: Session) -> User:
    """
    Retrieves a single User record by their primary key.

    Intended for use by the frontend session layer to re-hydrate the
    current user context (e.g., after loading a saved session token).

    Args:
        user_id: The integer primary key of the target User.
        db:      An active SQLAlchemy Session.

    Returns:
        The User ORM object if found.

    Raises:
        ValueError: If no User exists with the given UserID.
    """
    user: Optional[User] = db.get(User, user_id)
    if user is None:
        raise ValueError(f"No user found with UserID={user_id}.")
    return user


def update_user_password(user_id: int, current_password: str, new_password: str, db: Session) -> None:
    """
    Updates the password for an existing user after verifying their current password.

    Args:
        user_id:           The ID of the user to update.
        current_password:  The existing plain-text password for verification.
        new_password:      The new plain-text password to set.
        db:                An active SQLAlchemy Session.

    Raises:
        ValueError: If current password verification fails or new password is too weak.
    """
    user = get_user_by_id(user_id, db)

    if not user.verify_password(current_password):
        logger.warning("Password update failed: Incorrect current password for user_id=%d.", user_id)
        raise ValueError("Current password is incorrect.")

    if not new_password or len(new_password) < 8:
        raise ValueError("New password must be at least 8 characters long.")

    user.set_password(new_password)
    db.commit()
    logger.info("Password updated successfully for user_id=%d.", user_id)
