"""Empresas e usuários do app.

Não existe cadastro aberto: só a equipe DriveSafe (admin) cria acessos, reativa, troca o login ou redefine senha.
O gestor vê os acessos da própria empresa e pode bloquear um deles na hora (ex.: motorista desligado).
"""
import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backend.auth import Principal, audit, ensure_company_access, require_roles, scoped_company
from backend.database import Company, Driver, User, UserSession, get_db
from backend.identifiers import email_problem, format_phone, normalize_email, normalize_phone
from backend.queries import company_counts
from backend.schemas import CompanyIn, CompanyOut, CompanyPatch, UserCreatedOut, UserIn, UserOut, UserPatch
from backend.security import hash_password, password_problem
from backend.serializers import company_out, user_out

router = APIRouter(tags=["empresas e usuários"])

ASK_THE_TEAM = "Para criar, reativar ou alterar um acesso, fale com a equipe DriveSafe pelo celular."
PHONE_HINT = "Celular inválido. Informe com DDD, por exemplo (11) 98765-4321."


def temporary_password() -> str:
    return secrets.token_urlsafe(9)


def parse_email(raw: Optional[str]) -> Optional[str]:
    email = normalize_email(raw)
    problem = email_problem(email)
    if problem:
        raise HTTPException(status_code=400, detail=problem)
    return email


def parse_phone(raw: Optional[str], hint: str = PHONE_HINT) -> Optional[str]:
    if raw is None or not str(raw).strip():
        return None
    phone = normalize_phone(raw)
    if phone is None:
        raise HTTPException(status_code=400, detail=hint)
    return phone


def ensure_login_free(db: Session, email: Optional[str], phone: Optional[str], user_id: int = 0) -> None:
    if email and db.query(User.id).filter(func.lower(User.email) == email, User.id != user_id).first():
        raise HTTPException(status_code=409, detail="Já existe um acesso com este e-mail.")
    if phone and db.query(User.id).filter(User.phone == phone, User.id != user_id).first():
        raise HTTPException(status_code=409, detail="Já existe um acesso com este celular.")


def login_label(user: User) -> str:
    return user.email or format_phone(user.phone) or f"usuario:{user.id}"


# ---------- empresas ----------

@router.get("/api/companies", response_model=List[CompanyOut])
def list_companies(principal: Principal = Depends(require_roles("admin", "gestor")), db: Session = Depends(get_db)):
    query = db.query(Company).order_by(Company.name)
    if not principal.is_admin:
        query = query.filter(Company.id == principal.company_id)
    companies = query.all()
    counts = company_counts(db, [company.id for company in companies])
    return [company_out(company, counts) for company in companies]


@router.post("/api/companies", response_model=CompanyOut, status_code=201)
def create_company(payload: CompanyIn, request: Request, principal: Principal = Depends(require_roles("admin")),
                   db: Session = Depends(get_db)):
    company = Company(
        name=payload.name.strip(), document=(payload.document or "").strip() or None,
        contact_name=(payload.contact_name or "").strip() or None,
        contact_phone=parse_phone(payload.contact_phone, "Celular do responsável inválido. Informe com DDD."),
        activation_policy=payload.activation_policy,
    )
    db.add(company)
    db.flush()
    audit(db, principal, "empresa_criada", target=company.name, request=request, company_id=company.id)
    db.commit()
    db.refresh(company)
    return company_out(company, {})


@router.patch("/api/companies/{company_id}", response_model=CompanyOut)
def update_company(company_id: int, payload: CompanyPatch, request: Request,
                   principal: Principal = Depends(require_roles("admin", "gestor")), db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    ensure_company_access(principal, company.id)
    changes = payload.model_dump(exclude_unset=True)
    if not principal.is_admin and set(changes) - {"activation_policy"}:
        raise HTTPException(status_code=403, detail="Só a equipe DriveSafe altera os dados cadastrais da empresa.")
    for field, value in changes.items():
        if field == "contact_phone":
            value = parse_phone(value, "Celular do responsável inválido. Informe com DDD.")
        elif isinstance(value, str):
            value = value.strip() or None
        if field in ("name", "activation_policy", "active") and value is None:
            raise HTTPException(status_code=400, detail="Preencha este campo.")
        setattr(company, field, value)
    audit(db, principal, "empresa_alterada", target=company.name, details=changes, request=request,
          company_id=company.id)
    db.commit()
    db.refresh(company)
    return company_out(company, company_counts(db, [company.id]))


# ---------- usuários ----------

@router.get("/api/users", response_model=List[UserOut])
def list_users(company_id: Optional[int] = None, principal: Principal = Depends(require_roles("admin", "gestor")),
               db: Session = Depends(get_db)):
    scope = scoped_company(principal, company_id)
    query = db.query(User).options(joinedload(User.company), joinedload(User.driver)).order_by(User.name)
    if scope is not None:
        query = query.filter(User.company_id == scope)
    return [user_out(user) for user in query.all()]


@router.post("/api/users", response_model=UserCreatedOut, status_code=201)
def create_user(payload: UserIn, request: Request, principal: Principal = Depends(require_roles("admin")),
                db: Session = Depends(get_db)):
    role = payload.role
    company_id = None if role == "admin" else payload.company_id
    if role != "admin" and (company_id is None or db.get(Company, company_id) is None):
        raise HTTPException(status_code=400, detail="Escolha a empresa do usuário.")

    driver_id = None
    if role == "motorista":
        driver = db.get(Driver, payload.driver_id) if payload.driver_id else None
        if driver is None or driver.company_id != company_id:
            raise HTTPException(status_code=400, detail="Escolha um motorista cadastrado nesta empresa.")
        if db.query(User.id).filter(User.driver_id == driver.id).first():
            raise HTTPException(status_code=409, detail="Este motorista já tem acesso ao app.")
        driver_id = driver.id

    email, phone = parse_email(payload.email), parse_phone(payload.phone)
    if not email and not phone:
        raise HTTPException(status_code=400, detail="Informe o e-mail ou o celular que a pessoa vai usar para entrar.")
    ensure_login_free(db, email, phone)

    temporary = None
    if payload.password:
        problem = password_problem(payload.password)
        if problem:
            raise HTTPException(status_code=400, detail=problem)
        password = payload.password
    else:
        temporary = password = temporary_password()

    user = User(name=payload.name.strip(), email=email, phone=phone, password_hash=hash_password(password), role=role,
                company_id=company_id, driver_id=driver_id, must_change_password=temporary is not None)
    db.add(user)
    db.flush()
    audit(db, principal, "usuario_criado", target=login_label(user), details={"papel": role}, request=request,
          company_id=company_id)
    db.commit()
    db.refresh(user)
    return UserCreatedOut(user=user_out(user), temporary_password=temporary)


@router.patch("/api/users/{user_id}", response_model=UserCreatedOut)
def update_user(user_id: int, payload: UserPatch, request: Request,
                principal: Principal = Depends(require_roles("admin", "gestor")), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None or (not principal.is_admin and (user.role == "admin" or user.company_id != principal.company_id)):
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    changes = payload.model_dump(exclude_unset=True)
    if not principal.is_admin and (set(changes) != {"active"} or changes["active"] is not False):
        raise HTTPException(status_code=403, detail=ASK_THE_TEAM)
    if user.id == principal.user.id and changes.get("active") is False:
        raise HTTPException(status_code=400, detail="Você não pode bloquear o próprio acesso.")

    end_sessions = False
    if changes.get("name"):
        user.name = changes["name"].strip()
    if "email" in changes or "phone" in changes:
        email = parse_email(changes["email"]) if "email" in changes else user.email
        phone = parse_phone(changes["phone"]) if "phone" in changes else user.phone
        if not email and not phone:
            raise HTTPException(status_code=400, detail="O acesso precisa de e-mail ou celular.")
        ensure_login_free(db, email, phone, user.id)
        user.email, user.phone = email, phone
    if changes.get("active") is not None:
        user.active = changes["active"]
        end_sessions = not changes["active"]
    temporary = None
    if changes.get("reset_password"):
        temporary = temporary_password()
        user.password_hash = hash_password(temporary)
        user.must_change_password = True
        end_sessions = True
    if end_sessions:
        db.query(UserSession).filter(UserSession.user_id == user.id).delete(synchronize_session=False)
    audit(db, principal, "usuario_alterado", target=login_label(user),
          details={"campos": sorted(changes), "ativo": changes.get("active")}, request=request,
          company_id=user.company_id)
    db.commit()
    db.refresh(user)
    return UserCreatedOut(user=user_out(user), temporary_password=temporary)
