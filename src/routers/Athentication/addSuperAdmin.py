import logging

from DB.database import SessionLocal
from models.office import Office
from models.user import User
from routers.Athentication.user_services import pwd_context
from schemas.user import UserRole, Status
from sqlalchemy import text
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Superadmin details

SUPERADMIN_ROLE = UserRole.ADMIN

SUPERADMIN_NATIONAL_CODE = "123"
SUPERADMIN_NAME = "admin"
SUPERADMIN_Status = Status.ACTIVE


def register_superadmin():
    db = SessionLocal()
    try:
        # Ensure office with id=1 exists
        super_office = db.query(Office).filter(Office.id == 1).first()
        if not super_office:
            super_office = Office(id=1, name="all")
            db.add(super_office)
            db.commit()
            # به‌روزرسانی sequence جدول بعد از افزودن رکورد با id=1
            db.execute(text("SELECT setval(pg_get_serial_sequence('offices', 'id'), 1, true)"))
            db.commit()

        # Check if the superadmin already exists
        superadmin = db.query(User).filter(User.code == SUPERADMIN_NATIONAL_CODE).first()
        if not superadmin:
            password = '123'
            hashed_password = pwd_context.hash(password)

            superadmin_user = User(
                code=SUPERADMIN_NATIONAL_CODE,
                name=SUPERADMIN_NAME,
                family="admin",
                password=hashed_password,
                role=SUPERADMIN_ROLE,
                status=SUPERADMIN_Status,
                office_id=1
            )

            db.add(superadmin_user)
            db.commit()
            logging.info("Superadmin user created successfully.")
        else:
            logging.info("Superadmin user already exists.")
    except Exception as e:
        db.rollback()
        logging.error(f"Error creating superadmin: {e}")
    finally:
        db.close()

