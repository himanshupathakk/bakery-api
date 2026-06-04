from flask_jwt_extended import get_jwt_identity
from flask_smorest import abort
from models import UserModel

#Check if the current JWT user has admin role.
def admin_required():
    
    user_id = int(get_jwt_identity())
    user = UserModel.query.get(user_id)
    if not user or user.role != "admin":
        abort(403, message="Admin access required. You do not have permission to perform this action.")
