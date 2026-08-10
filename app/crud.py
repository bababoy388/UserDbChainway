from app import models, security


def get_ore_by_epc(db, epc):
    return db.query(models.OreMapping).filter(models.OreMapping.epc == epc).first()

def get_user_by_username(db, username):
    return db.query(models.User).filter(models.User.username == username).first()

def authenticate_user(db, username, password):
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not security.verify_password(password, user.hashed_password):
        return None
    return user