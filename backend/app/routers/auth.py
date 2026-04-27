from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import CurrentUserResponse, LoginRequest, LoginResponse
from app.services.auth import authenticate_user, create_access_token, current_user_to_response

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """Login with username and password."""
    user = authenticate_user(db, data.username, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return LoginResponse(
        access_token=create_access_token(user),
        user=CurrentUserResponse(**current_user_to_response(user)),
    )


@router.get("/me", response_model=CurrentUserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> CurrentUserResponse:
    """Get current user profile and permissions."""
    return CurrentUserResponse(**current_user_to_response(current_user))
