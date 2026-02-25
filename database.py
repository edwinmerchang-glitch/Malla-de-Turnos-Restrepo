from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///data.db", connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)
Base = declarative_base()

class Empleado(Base):
    __tablename__ = "empleados"
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    usuario = Column(String, unique=True)
    password = Column(String)
    rol = Column(String)  # admin / empleado

class Turno(Base):
    __tablename__ = "turnos"
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    inicio = Column(String)
    fin = Column(String)

class Asignacion(Base):
    __tablename__ = "asignaciones"
    id = Column(Integer, primary_key=True)
    empleado_id = Column(Integer, ForeignKey("empleados.id"))
    fecha = Column(Date)
    turno = Column(String)

Base.metadata.create_all(engine)

# ---- CREAR ADMIN POR DEFECTO SI NO EXISTE ----
session = Session()

if session.query(Empleado).count() == 0:
    admin = Empleado(
        nombre="Administrador",
        usuario="admin",
        password="admin123",
        rol="admin"
    )
    session.add(admin)
    session.commit()
    print("✅ Usuario admin creado: admin / admin123")