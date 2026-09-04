from fastapi import APIRouter, HTTPException, Request, status
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from sqlalchemy import select
from redis.asyncio import Redis
from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import User
from app.schemas.user import AuthResponse, GoogleLoginRequest, LoginRequest, RegisterRequest
router=APIRouter(tags=["auth"]); settings=get_settings()
async def _rate_limit(request:Request):
    try:
        redis=Redis.from_url(settings.REDIS_URL,decode_responses=True); key=f"auth:login:{request.client.host if request.client else 'unknown'}"; count=await redis.incr(key)
        if count==1: await redis.expire(key,60)
        await redis.aclose()
        if count>settings.LOGIN_RATE_LIMIT_PER_MINUTE: raise HTTPException(429,"Too many login attempts. Try again shortly.")
    except HTTPException: raise
    except Exception: return
@router.post("/register",response_model=AuthResponse,status_code=201)
async def register(payload:RegisterRequest,db:DbSession):
    if payload.password!=payload.password_confirmation: raise HTTPException(422,{"errors":{"password":["The password confirmation does not match."]}})
    if len(payload.password)<8: raise HTTPException(422,{"errors":{"password":["The password must be at least 8 characters."]}})
    if await db.scalar(select(User.id).where(User.email==payload.email)): raise HTTPException(422,{"errors":{"email":["The email has already been taken."]}})
    user=User(name=payload.name.strip(),email=payload.email,password_hash=hash_password(payload.password)); db.add(user); await db.commit(); await db.refresh(user)
    return AuthResponse(user=user,token=create_access_token(user.id,token_version=user.token_version))
@router.post("/login",response_model=AuthResponse)
async def login(payload:LoginRequest,request:Request,db:DbSession):
    await _rate_limit(request); user=await db.scalar(select(User).where(User.email==payload.email))
    if user is None or not verify_password(payload.password,user.password_hash): raise HTTPException(422,{"errors":{"email":["The provided credentials are incorrect."]}})
    return AuthResponse(user=user,token=create_access_token(user.id,token_version=user.token_version))
@router.post("/google",response_model=AuthResponse)
async def google_login(payload:GoogleLoginRequest,request:Request,db:DbSession):
    await _rate_limit(request)
    ids={x.strip() for x in settings.GOOGLE_CLIENT_IDS.split(",") if x.strip()}
    if not ids: raise HTTPException(503,"Google sign-in is not configured.")
    try: claims=id_token.verify_oauth2_token(payload.id_token,google_requests.Request(),clock_skew_in_seconds=10)
    except ValueError: raise HTTPException(401,"Invalid Google identity token.")
    if claims.get("aud") not in ids or claims.get("iss") not in {"accounts.google.com","https://accounts.google.com"}: raise HTTPException(401,"Google identity could not be verified.")
    sub=str(claims.get("sub", "")); email=str(claims.get("email", "")).lower().strip()
    if not sub or not email or claims.get("email_verified") is not True: raise HTTPException(401,"A verified Google account is required.")
    user=await db.scalar(select(User).where((User.google_sub==sub)|(User.email==email)))
    if user is None:
        user=User(name=str(claims.get("name") or email.split("@")[0])[:255],email=email,password_hash=hash_password(__import__("secrets").token_urlsafe(32)),google_sub=sub,avatar_url=claims.get("picture")); db.add(user)
    else:
        if not user.is_active:
            raise HTTPException(403, "This account is suspended.")
        if user.google_sub and user.google_sub!=sub:
            raise HTTPException(409,"This email is linked to another Google identity.")
        user.google_sub=sub
        if not user.avatar_url and claims.get("picture"): user.avatar_url=str(claims["picture"])
    await db.commit(); await db.refresh(user)
    return AuthResponse(user=user,token=create_access_token(user.id,token_version=user.token_version))
@router.post("/logout")
async def logout(current_user:CurrentUser,db:DbSession): current_user.token_version+=1; await db.commit(); return {"message":"Logged out"}
@router.post("/admin/session",response_model=dict)
async def admin_session(payload:LoginRequest,current_user:CurrentUser,db:DbSession):
    if current_user.role!="SUPER_ADMIN" or payload.email.lower()!=current_user.email.lower() or not verify_password(payload.password,current_user.password_hash): raise HTTPException(403,"Admin console authorization failed.")
    return {"token":create_access_token(current_user.id,expires_minutes=settings.ADMIN_SESSION_EXPIRE_MINUTES,scope="admin",token_version=current_user.token_version),"expires_in":settings.ADMIN_SESSION_EXPIRE_MINUTES*60}
