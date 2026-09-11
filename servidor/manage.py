"""Administração do servidor DriveSafe AI pela linha de comando.

Não há cadastro aberto no app: quem quer acesso fala com a equipe pelo celular, e a equipe cria o login aqui
(ou pelo app, com perfil admin). O login pode ser o e-mail ou o celular da pessoa.

Primeiros passos:
  python manage.py criar-usuario --papel admin --nome "Seu nome" --email voce@exemplo.com
  python manage.py criar-empresa --nome "Transportadora Exemplo" --contato "Fulana" --celular "(11) 98765-4321"
  python manage.py criar-usuario --papel gestor --nome "Fulana" --celular "(11) 98765-4321" --empresa 1
  python manage.py criar-dispositivo --nome "Caminhão ABC-1234" --empresa 1

Para testar o app com dados de exemplo:
  python manage.py demo --com-alertas

Senhas: sem DRIVESAFE_SENHA_INICIAL, o comando gera uma senha temporária, mostra uma única vez e pede a troca no
primeiro acesso.
"""
import argparse
import os
import random
import secrets
import uuid
from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from backend.alert_types import needs_review
from backend.identifiers import email_problem, format_phone, normalize_email, normalize_phone
from backend.database import (
    ACTIVATION_POLICIES, ROLES, Alert, Company, Consent, CONSENT_TERM_VERSION, Device, Driver, SessionLocal, User,
    UserSession, Vehicle, format_local, init_db, utcnow,
)
from backend.security import generate_device_token, hash_password, password_problem


def _get_or_exit(db, model, object_id, label):
    obj = db.get(model, object_id)
    if obj is None:
        raise SystemExit(f"{label} #{object_id} não existe.")
    return obj


def _company(db, company_id):
    if company_id is not None:
        return _get_or_exit(db, Company, company_id, "Empresa")
    companies = db.query(Company).order_by(Company.id).limit(2).all()
    if len(companies) == 1:
        return companies[0]
    if not companies:
        raise SystemExit('Nenhuma empresa cadastrada. Crie uma antes: python manage.py criar-empresa --nome "Nome"')
    raise SystemExit("Há mais de uma empresa: informe --empresa ID (veja com: python manage.py empresas).")


def _commit_or_exit(db, message):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise SystemExit(message)


def _password():
    """(senha, é temporária?)"""
    chosen = os.environ.get("DRIVESAFE_SENHA_INICIAL")
    if chosen:
        problem = password_problem(chosen)
        if problem:
            raise SystemExit(problem)
        return chosen, False
    return secrets.token_urlsafe(9), True


def _phone_or_exit(raw):
    if not raw:
        return None
    phone = normalize_phone(raw)
    if phone is None:
        raise SystemExit("Celular inválido. Informe com DDD, por exemplo (11) 98765-4321.")
    return phone


def _login_of(user):
    return " / ".join(filter(None, (user.email, format_phone(user.phone)))) or "-"


def _print_token(token):
    print()
    print("Token do dispositivo (aparece só agora, guarde em lugar seguro):")
    print(f"  {token}")
    print()
    print("Configure no dispositivo:")
    print("  DRIVESAFE_SERVER_URL=http://<ip-do-servidor>:8000")
    print(f"  DRIVESAFE_DEVICE_TOKEN={token}")


# ---------- empresas e usuários ----------

def criar_empresa(db, args):
    company = Company(name=args.nome, document=args.documento, contact_name=args.contato,
                      contact_phone=_phone_or_exit(args.celular), activation_policy=args.politica)
    db.add(company)
    db.commit()
    print(f'Empresa #{company.id} "{company.name}" criada (sinais de ativação: {company.activation_policy}).')


def listar_empresas(db, _args):
    for company in db.query(Company).order_by(Company.id).all():
        status = "ativa" if company.active else "INATIVA"
        contact = " ".join(filter(None, (company.contact_name, format_phone(company.contact_phone)))) or "-"
        print(f"#{company.id:<3} {company.name:<36} {company.document or '-':<18} contato {contact:<36} "
              f"ativação {company.activation_policy:<9} {status}")


def criar_usuario(db, args):
    company_id = driver_id = None
    if args.papel != "admin":
        company_id = _company(db, args.empresa).id
    if args.papel == "motorista":
        if args.motorista is None:
            raise SystemExit("Informe --motorista ID para usuário motorista.")
        driver = _get_or_exit(db, Driver, args.motorista, "Motorista")
        if driver.company_id != company_id:
            raise SystemExit("O motorista não pertence a esta empresa.")
        driver_id = driver.id
    email = normalize_email(args.email)
    problem = email_problem(email)
    if problem:
        raise SystemExit(problem)
    phone = _phone_or_exit(args.celular)
    if not email and not phone:
        raise SystemExit("Informe --email ou --celular: é o que a pessoa vai usar para entrar no app.")
    if email and db.query(User.id).filter(func.lower(User.email) == email).first():
        raise SystemExit(f"Já existe usuário com o e-mail {email}.")
    if phone and db.query(User.id).filter(User.phone == phone).first():
        raise SystemExit(f"Já existe usuário com o celular {format_phone(phone)}.")
    password, temporary = _password()
    user = User(name=args.nome, email=email, phone=phone, password_hash=hash_password(password), role=args.papel,
                company_id=company_id, driver_id=driver_id, must_change_password=temporary)
    db.add(user)
    db.commit()
    print(f"Usuário #{user.id} {_login_of(user)} ({user.role}) criado.")
    if temporary:
        print(f"Senha temporária (aparece só agora; será pedida a troca no primeiro acesso): {password}")


def listar_usuarios(db, _args):
    for user in db.query(User).order_by(User.id).all():
        company = user.company.name if user.company else "-"
        status = "ativo" if user.active else "INATIVO"
        print(f"#{user.id:<3} {_login_of(user):<52} {user.role:<10} {company:<28} {status}")


def redefinir_senha(db, args):
    user = _get_or_exit(db, User, args.id, "Usuário")
    password, temporary = _password()
    user.password_hash = hash_password(password)
    user.must_change_password = temporary
    db.query(UserSession).filter(UserSession.user_id == user.id).delete(synchronize_session=False)
    db.commit()
    print(f"Senha de {_login_of(user)} redefinida; sessões abertas foram encerradas.")
    if temporary:
        print(f"Senha temporária (aparece só agora): {password}")


# ---------- dispositivos ----------

def criar_dispositivo(db, args):
    company = _company(db, args.empresa)
    for model, value, label in ((Vehicle, args.veiculo, "Veículo"), (Driver, args.motorista, "Motorista")):
        if value is not None and _get_or_exit(db, model, value, label).company_id != company.id:
            raise SystemExit(f"{label} #{value} não pertence à empresa {company.name}.")
    token, token_hash, prefix = generate_device_token()
    device = Device(name=args.nome, company_id=company.id, token_hash=token_hash, token_prefix=prefix,
                    vehicle_id=args.veiculo, driver_id=args.motorista)
    db.add(device)
    db.commit()
    print(f'Dispositivo #{device.id} "{device.name}" criado na empresa {company.name}.')
    _print_token(token)


def novo_token(db, args):
    device = _get_or_exit(db, Device, args.id, "Dispositivo")
    token, token_hash, prefix = generate_device_token()
    device.token_hash = token_hash
    device.token_prefix = prefix
    device.revoked_at = None
    db.commit()
    print(f'Novo token para #{device.id} "{device.name}". O token anterior parou de funcionar.')
    _print_token(token)


def revogar_dispositivo(db, args):
    device = _get_or_exit(db, Device, args.id, "Dispositivo")
    device.revoked_at = utcnow()
    db.commit()
    print(f'Dispositivo #{device.id} "{device.name}" revogado. Os alertas antigos continuam salvos.')


def vincular_dispositivo(db, args):
    device = _get_or_exit(db, Device, args.id, "Dispositivo")
    if args.veiculo is not None:
        vehicle = None if args.veiculo == 0 else _get_or_exit(db, Vehicle, args.veiculo, "Veículo")
        if vehicle is not None and vehicle.company_id != device.company_id:
            raise SystemExit("O veículo é de outra empresa.")
        device.vehicle_id = vehicle.id if vehicle else None
    if args.motorista is not None:
        driver = None if args.motorista == 0 else _get_or_exit(db, Driver, args.motorista, "Motorista")
        if driver is not None and driver.company_id != device.company_id:
            raise SystemExit("O motorista é de outra empresa.")
        device.driver_id = driver.id if driver else None
    db.commit()
    db.refresh(device)
    vehicle = device.vehicle.plate if device.vehicle else "nenhum"
    driver = device.driver.name if device.driver else "nenhum"
    print(f'Dispositivo #{device.id} "{device.name}": veículo {vehicle}, motorista {driver}.')


def listar_dispositivos(db, _args):
    devices = db.query(Device).order_by(Device.id).all()
    if not devices:
        print('Nenhum dispositivo cadastrado. Use: python manage.py criar-dispositivo --nome "Nome"')
        return
    for device in devices:
        if device.revoked_at:
            status = "REVOGADO"
        elif device.last_seen_at is None:
            status = "nunca conectou"
        else:
            status = f"último contato {format_local(device.last_seen_at)}"
        vehicle = device.vehicle.plate if device.vehicle else "-"
        driver = device.driver.name if device.driver else "-"
        company = device.company.name if device.company else "-"
        print(f"#{device.id:<3} {device.name:<28} {company:<24} token {device.token_prefix}...  veículo {vehicle:<9} "
              f"motorista {driver:<18} {status}")


# ---------- motoristas e veículos ----------

def listar_veiculos(db, _args):
    for vehicle in db.query(Vehicle).order_by(Vehicle.id).all():
        company = vehicle.company.name if vehicle.company else "-"
        print(f"#{vehicle.id:<3} {vehicle.plate:<10} {vehicle.model or '-':<22} {vehicle.type or '-':<12} {company}")


def listar_motoristas(db, _args):
    for driver in db.query(Driver).order_by(Driver.id).all():
        company = driver.company.name if driver.company else "-"
        print(f"#{driver.id:<3} {driver.name:<28} CNH {driver.license_number or '-':<12} {driver.phone or '-':<14} {company}")


def criar_veiculo(db, args):
    vehicle = Vehicle(plate=args.placa.upper(), model=args.modelo, type=args.tipo, company_id=_company(db, args.empresa).id)
    db.add(vehicle)
    _commit_or_exit(db, f"Já existe um veículo com a placa {args.placa}.")
    print(f"Veículo #{vehicle.id} {vehicle.plate} criado.")


def criar_motorista(db, args):
    driver = Driver(name=args.nome, license_number=args.cnh.upper(), phone=args.telefone,
                    company_id=_company(db, args.empresa).id)
    db.add(driver)
    _commit_or_exit(db, f"Já existe um motorista com a CNH {args.cnh}.")
    print(f"Motorista #{driver.id} {driver.name} criado.")


# ---------- demonstração ----------

DEMO_COMPANY = "Transportadora Demonstração"
DEMO_DRIVERS = (("Ana Ribeiro", "DEMO000001"), ("Carlos Menezes", "DEMO000002"), ("Joana Prado", "DEMO000003"))
DEMO_VEHICLES = (("DMO-1A01", "Volvo FH 540", "Caminhão"), ("DMO-2B02", "Scania R 450", "Caminhão"),
                 ("DMO-3C03", "Mercedes-Benz O500", "Ônibus"))
DEMO_EVENTS = (("atencao", 2), ("sonolencia", 3), ("microssono", 3), ("celular_na_mao", 3), ("olhando_celular", 4),
               ("celular_no_ouvido", 3), ("sono", 4), ("direcao_continua", 2), ("olhos_nao_visiveis", 1))


def demo(db, args):
    company = db.query(Company).filter(Company.name == DEMO_COMPANY).first()
    if company is None:
        company = Company(name=DEMO_COMPANY, document="00.000.000/0001-00", activation_policy="local")
        db.add(company)
        db.flush()
    drivers = []
    for name, license_number in DEMO_DRIVERS:
        driver = db.query(Driver).filter(Driver.license_number == license_number).first()
        if driver is None:
            driver = Driver(name=name, license_number=license_number, company_id=company.id)
            db.add(driver)
        drivers.append(driver)
    vehicles = []
    for plate, model, kind in DEMO_VEHICLES:
        vehicle = db.query(Vehicle).filter(Vehicle.plate == plate).first()
        if vehicle is None:
            vehicle = Vehicle(plate=plate, model=model, type=kind, company_id=company.id)
            db.add(vehicle)
        vehicles.append(vehicle)
    db.flush()

    created_users = []
    for email, name, role, driver in (("gestor.demo@drivesafe.local", "Gestora Demonstração", "gestor", None),
                                      ("motorista.demo@drivesafe.local", DEMO_DRIVERS[0][0], "motorista", drivers[0])):
        if db.query(User.id).filter(User.email == email).first():
            continue
        password, temporary = _password()
        db.add(User(name=name, email=email, password_hash=hash_password(password), role=role, company_id=company.id,
                    driver_id=driver.id if driver else None, must_change_password=temporary))
        created_users.append((email, password if temporary else "(DRIVESAFE_SENHA_INICIAL)"))

    tokens = []
    for index, (driver, vehicle) in enumerate(zip(drivers, vehicles), start=1):
        name = f"Demonstração {index} ({vehicle.plate})"
        if db.query(Device.id).filter(Device.name == name).first():
            continue
        token, token_hash, prefix = generate_device_token()
        db.add(Device(name=name, company_id=company.id, token_hash=token_hash, token_prefix=prefix,
                      vehicle_id=vehicle.id, driver_id=driver.id))
        tokens.append((name, token))

    if not db.query(Consent.id).filter(Consent.driver_id == drivers[0].id).first():
        db.add(Consent(driver_id=drivers[0].id, kind="monitoramento", granted=True, term_version=CONSENT_TERM_VERSION,
                       channel="admin", note="Dado de demonstração"))

    added = 0
    if args.com_alertas:
        rng = random.Random(7)
        now = utcnow()
        devices = {device.driver_id: device for device in db.query(Device).filter(Device.company_id == company.id)}
        for _ in range(60):
            driver = rng.choice(drivers)
            alert_type, risk = rng.choice(DEMO_EVENTS)
            moment = now - timedelta(days=rng.uniform(0, 7), hours=rng.uniform(0, 6))
            device = devices.get(driver.id)
            db.add(Alert(
                event_uid=str(uuid.uuid4()), company_id=company.id, driver_id=driver.id,
                vehicle_id=device.vehicle_id if device else None, device_id=device.id if device else None,
                alert_type=alert_type, risk_level=risk, duration=round(rng.uniform(0.5, 6.0), 2),
                details='{"demo": true}', timestamp=moment, received_at=moment,
                review_status="pendente" if needs_review(alert_type, risk) else "arquivado",
            ))
            added += 1
    db.commit()

    print(f'Empresa de demonstração: #{company.id} "{company.name}" com {len(drivers)} motoristas e {len(vehicles)} veículos.')
    for email, password in created_users:
        print(f"  usuário {email}  senha temporária: {password}")
    for name, token in tokens:
        print(f"  dispositivo {name}  token: {token}")
    if added:
        print(f"  {added} alertas de exemplo nos últimos 7 dias (details com \"demo\": true).")


def build_parser():
    parser = argparse.ArgumentParser(description="Administração do servidor DriveSafe AI.")
    sub = parser.add_subparsers(dest="comando", required=True, metavar="comando")

    p = sub.add_parser("criar-empresa", help="cadastra uma transportadora")
    p.add_argument("--nome", required=True)
    p.add_argument("--documento", help="CNPJ")
    p.add_argument("--contato", help="nome do responsável na transportadora")
    p.add_argument("--celular", help="celular do responsável, com DDD")
    p.add_argument("--politica", choices=ACTIVATION_POLICIES, default="local", help="sinais de ativação atípica")
    p.set_defaults(func=criar_empresa)

    p = sub.add_parser("empresas", help="lista as empresas")
    p.set_defaults(func=listar_empresas)

    p = sub.add_parser("criar-usuario", help="cria acesso ao app (admin, gestor ou motorista)")
    p.add_argument("--papel", choices=ROLES, required=True)
    p.add_argument("--nome", required=True)
    p.add_argument("--email", help="login por e-mail")
    p.add_argument("--celular", help="login por celular, com DDD (pode usar junto com --email)")
    p.add_argument("--empresa", type=int, help="ID da empresa (gestor e motorista)")
    p.add_argument("--motorista", type=int, help="ID do motorista (papel motorista)")
    p.set_defaults(func=criar_usuario)

    p = sub.add_parser("usuarios", help="lista os usuários do app")
    p.set_defaults(func=listar_usuarios)

    p = sub.add_parser("redefinir-senha", help="gera senha temporária e encerra as sessões do usuário")
    p.add_argument("id", type=int)
    p.set_defaults(func=redefinir_senha)

    p = sub.add_parser("criar-dispositivo", help="cadastra um dispositivo e mostra o token dele")
    p.add_argument("--nome", required=True)
    p.add_argument("--empresa", type=int, help="ID da empresa (obrigatório se houver mais de uma)")
    p.add_argument("--veiculo", type=int, help="ID do veículo")
    p.add_argument("--motorista", type=int, help="ID do motorista")
    p.set_defaults(func=criar_dispositivo)

    p = sub.add_parser("dispositivos", help="lista os dispositivos")
    p.set_defaults(func=listar_dispositivos)

    p = sub.add_parser("vincular-dispositivo", help="liga o dispositivo a um veículo/motorista (0 desliga)")
    p.add_argument("id", type=int)
    p.add_argument("--veiculo", type=int)
    p.add_argument("--motorista", type=int)
    p.set_defaults(func=vincular_dispositivo)

    p = sub.add_parser("novo-token", help="gera um token novo e invalida o anterior")
    p.add_argument("id", type=int)
    p.set_defaults(func=novo_token)

    p = sub.add_parser("revogar-dispositivo", help="bloqueia o dispositivo (ex.: equipamento roubado)")
    p.add_argument("id", type=int)
    p.set_defaults(func=revogar_dispositivo)

    p = sub.add_parser("veiculos", help="lista os veículos")
    p.set_defaults(func=listar_veiculos)

    p = sub.add_parser("criar-veiculo", help="cadastra um veículo")
    p.add_argument("--placa", required=True)
    p.add_argument("--modelo", required=True)
    p.add_argument("--tipo", required=True)
    p.add_argument("--empresa", type=int)
    p.set_defaults(func=criar_veiculo)

    p = sub.add_parser("motoristas", help="lista os motoristas")
    p.set_defaults(func=listar_motoristas)

    p = sub.add_parser("criar-motorista", help="cadastra um motorista")
    p.add_argument("--nome", required=True)
    p.add_argument("--cnh", required=True)
    p.add_argument("--telefone")
    p.add_argument("--empresa", type=int)
    p.set_defaults(func=criar_motorista)

    p = sub.add_parser("demo", help="cria empresa, motoristas, veículos, usuários e dispositivos de demonstração")
    p.add_argument("--com-alertas", action="store_true", help="também cria alertas de exemplo dos últimos 7 dias")
    p.set_defaults(func=demo)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    init_db()
    db = SessionLocal()
    try:
        args.func(db, args)
    finally:
        db.close()


if __name__ == "__main__":
    main()
