import logging

from DB.database import SessionLocal
from models.office import Office
from models.user import User
from routers.Athentication.user_services import pwd_context
from schemas.user import UserRole, Status

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
        super_office = db.query(Office).filter(Office.id == 1)
        if not super_office:
            super_office = Office(
                name="all"
            )
        # Check if the superadmin already exists
        superadmin = db.query(User).filter(User.code == SUPERADMIN_NATIONAL_CODE).first()
        if not superadmin:
            password = '123'

            # Hash the password
            hashed_password = pwd_context.hash(password)

            # Create the superadmin user
            superadmin_user = User(
                code=SUPERADMIN_NATIONAL_CODE,
                name=SUPERADMIN_NAME,
                family="admin",
                password=hashed_password,
                role=SUPERADMIN_ROLE,
                status=SUPERADMIN_Status,
                office_id=1
            )

            # Add the superadmin to the database
            db.add(superadmin_user)
            db.commit()
        else:
            logging.info("Superadmin user already exists.")
    except Exception as e:
        db.rollback()
        logging.error(f"Error creating superadmin: {e}")
    finally:
        db.close()
