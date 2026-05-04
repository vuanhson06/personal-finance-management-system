import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models import Category, TransactionType

logger = logging.getLogger(__name__)

def create_category(user_id: int, name: str, cat_type: str, db: Session) -> Category:
    """
    Creates a new custom category for the user.
    """
    if not name or not name.strip():
        raise ValueError("Category name cannot be empty.")
        
    try:
        t_type = TransactionType(cat_type)
    except ValueError:
        raise ValueError(f"Invalid transaction type: {cat_type}. Must be 'Income' or 'Expense'.")

    # Optional: check if category with same name already exists for user
    existing = db.execute(
        select(Category).where(
            Category.UserID == user_id, 
            Category.CategoryName == name.strip()
        )
    ).scalar_one_or_none()
    
    if existing:
        raise ValueError(f"You already have a category named '{name.strip()}'.")

    try:
        cat = Category(
            UserID=user_id,
            CategoryName=name.strip(),
            Type=t_type
        )
        db.add(cat)
        db.commit()
        db.refresh(cat)
        logger.info("Category created: id=%d user=%d name='%s'", cat.CategoryID, user_id, cat.CategoryName)
        return cat
    except IntegrityError as e:
        db.rollback()
        raise RuntimeError("Failed to save category.") from e


def delete_category(category_id: int, user_id: int, db: Session) -> None:
    """
    Deletes a user-owned category.
    """
    cat = db.execute(
        select(Category).where(
            Category.CategoryID == category_id,
            Category.UserID == user_id
        )
    ).scalar_one_or_none()
    
    if not cat:
        raise ValueError(f"Category {category_id} not found or not owned by you.")
        
    # Check dependencies - SQLAlchemy handles cascade delete for transactions/budgets? 
    # Actually wait: DB constraint might restrict or cascade. 
    # To be safe, we let SQLAlchemy try, and if IntegrityError happens due to Foreign Key, we raise a user-friendly error.
    
    try:
        db.delete(cat)
        db.commit()
        logger.info("Category deleted: id=%d user=%d", category_id, user_id)
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Cannot delete category. It is likely currently in use by transactions or budgets.")
