import logging
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import User, UserRole

logger = logging.getLogger(__name__)


_EMAIL_REGEX = re.compile(r"^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z]{2,}$")
_PHONE_REGEX = re.compile(r"^\+?[\d\-\s\(\)]{7,15}$")


def _validate_email(email: str) -> None:
    if not _EMAIL_REGEX.match(email.strip()):
        raise ValueError(f"Invalid email format: '{email}'.")


def _validate_phone(phone: Optional[str]) -> None:
    if phone is not None and not _PHONE_REGEX.match(phone.strip()):
        raise ValueError(
            f"Invalid phone number format: '{phone}'. "
            "Expected format: +1-555-010-1001 or similar."
        )


def _check_email_unique(email: str, db: Session) -> None:
    existing: Optional[User] = db.execute(
        select(User).where(User.Email == email.strip().lower())
    ).scalar_one_or_none()
    if existing:
        raise ValueError(f"Email '{email}' is already registered.")


def _check_phone_unique(phone: Optional[str], db: Session) -> None:
    if phone is None:
        return
    existing: Optional[User] = db.execute(
        select(User).where(User.PhoneNumber == phone.strip())
    ).scalar_one_or_none()
    if existing:
        raise ValueError(f"Phone number '{phone}' is already registered.")


def register_user(username: str, email: str, password: str, db: Session, phone: Optional[str] = None, role: UserRole = UserRole.User,) -> User:
    if not username or not username.strip():
        raise ValueError("Username must not be empty.")
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")

    _validate_email(email)
    _validate_phone(phone)
    _check_email_unique(email, db)
    _check_phone_unique(phone, db)

    try:
        user = User(
            UserName=username.strip(),
            Email=email.strip().lower(),
            PhoneNumber=phone.strip() if phone else None,
            Role=role,
        )
        user.set_password(password)  

        db.add(user)
        db.commit()        
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
    _validate_email(email)

    user: Optional[User] = db.execute(
        select(User).where(User.Email == email.strip().lower())
    ).scalar_one_or_none()

    if user is None or not user.verify_password(password):
        logger.warning("Failed login attempt for email: '%s'.", email)
        raise ValueError("Invalid email or password.")

    if not user.IsActive:
        logger.warning("Blocked login attempt for deactivated account: '%s'.", email)
        raise ValueError("Your account has been deactivated. Please contact support.")

    logger.info(
        "User logged in: id=%d email='%s' role=%s.",
        user.UserID, user.Email, user.Role.value,
    )
    return user


def get_user_by_id(user_id: int, db: Session) -> User:
    user: Optional[User] = db.get(User, user_id)
    if user is None:
        raise ValueError(f"No user found with UserID={user_id}.")
    return user


def update_user_password(user_id: int, current_password: str, new_password: str, db: Session) -> None:
    user = get_user_by_id(user_id, db)

    if not user.verify_password(current_password):
        logger.warning("Password update failed: Incorrect current password for user_id=%d.", user_id)
        raise ValueError("Current password is incorrect.")

    if not new_password or len(new_password) < 8:
        raise ValueError("New password must be at least 8 characters long.")

    user.set_password(new_password)
    db.commit()
    logger.info("Password updated successfully for user_id=%d.", user_id)
