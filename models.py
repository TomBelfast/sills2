from datetime import datetime
import random
from extensions import db
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Mapped

class Client(db.Model):
    __allow_unmapped__ = True
    id: int = db.Column(db.Integer, primary_key=True)
    first_name: str = db.Column(db.String(50), nullable=False)
    last_name: str = db.Column(db.String(50), nullable=False)
    phone: str = db.Column(db.String(20), nullable=False)
    mobile: Optional[str] = db.Column(db.String(20), nullable=True)
    email: Optional[str] = db.Column(db.String(120), nullable=True)
    address: str = db.Column(db.String(200), nullable=False)
    town: str = db.Column(db.String(100), nullable=False)
    postal_code: str = db.Column(db.String(10), nullable=False)
    source: Optional[str] = db.Column(db.String(50), nullable=True)
    created_at: datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship without type annotation to avoid linter error
    sills = db.relationship('Sill', backref='client', lazy=True, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f'<Client {self.first_name} {self.last_name}>'

class Sill(db.Model):
    __allow_unmapped__ = True
    id: int = db.Column(db.Integer, primary_key=True)
    client_id: int = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    order_number: str = db.Column(db.String(20), unique=True, nullable=False)
    length: float = db.Column(db.Float, nullable=False)
    depth: float = db.Column(db.Float, nullable=False)
    high: Optional[float] = db.Column(db.Float, nullable=True)  # sill height
    angle: Optional[float] = db.Column(db.Float, nullable=True)  # angle in degrees
    color: str = db.Column(db.String(50), nullable=False)
    sill_type: str = db.Column(db.String(50), nullable=False)
    location: str = db.Column(db.String(100), nullable=False)
    has_95mm: bool = db.Column(db.Boolean, default=False)
    status: str = db.Column(db.String(20), default='active')
    order_date: datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @staticmethod
    def generate_order_number() -> str:
        return f"ORD-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'order_number': self.order_number,
            'client_id': self.client_id,
            'length': self.length,
            'depth': self.depth,
            'high': self.high,
            'angle': self.angle,
            'color': self.color,
            'sill_type': self.sill_type,
            'location': self.location,
            'has_95mm': self.has_95mm,
            'status': self.status,
            'order_date': self.order_date.strftime('%Y-%m-%d %H:%M:%S')
        }

class Settings(db.Model):
    __allow_unmapped__ = True
    id: int = db.Column(db.Integer, primary_key=True)
    plate_length: float = db.Column(db.Float, nullable=False, default=6000)  # mm
    length_95mm: float = db.Column(db.Float, nullable=False, default=200)   # mm
    cutting_allowance: float = db.Column(db.Float, nullable=False, default=2)  # mm
    
    # Material usage per meter
    hot_glue_per_meter: float = db.Column(db.Float, nullable=False, default=0.05)  # sticks/m
    glue_with_activator_per_meter: float = db.Column(db.Float, nullable=False, default=0.05)  # bottles/m
    silicone_per_meter: float = db.Column(db.Float, nullable=False, default=0.1)  # bottles/m
    silicone_color_per_meter: float = db.Column(db.Float, nullable=False, default=0.1)  # bottles/m
    pvc_cleaner_per_meter: float = db.Column(db.Float, nullable=False, default=0.1)  # bottles/m
    fixall_per_meter: float = db.Column(db.Float, nullable=False, default=0.1)  # bottles/m
    glue_color_extra: float = db.Column(db.Float, nullable=False, default=0.05)  # bottles/m extra for colored boards

class MaterialPrices(db.Model):
    __allow_unmapped__ = True
    id: int = db.Column(db.Integer, primary_key=True)
    # Board Prices
    gp_board_price: float = db.Column(db.Float, nullable=False, default=10.0)
    capit_board_price: float = db.Column(db.Float, nullable=False, default=10.0)
    board_95mm_price: float = db.Column(db.Float, nullable=False, default=10.0)
    
    # Glue and Silicone Prices
    glue_price: float = db.Column(db.Float, nullable=False, default=10.0)
    hot_glue_price: float = db.Column(db.Float, nullable=False, default=0.5)
    silicone_price: float = db.Column(db.Float, nullable=False, default=10.0)
    silicone_color_price: float = db.Column(db.Float, nullable=False, default=10.0)
    pvc_cleaner_price: float = db.Column(db.Float, nullable=False, default=10.0)
    s2_clear_silicone_price: float = db.Column(db.Float, nullable=False, default=10.0)
    fixall_white_price: float = db.Column(db.Float, nullable=False, default=10.0)
    glue_with_activator_price: float = db.Column(db.Float, nullable=False, default=10.0)
    
    # Fitting Prices
    fitting_price_straight: float = db.Column(db.Float, nullable=False, default=35.0)
    fitting_price_c_shape: float = db.Column(db.Float, nullable=False, default=35.0)
    fitting_price_bay_curve: float = db.Column(db.Float, nullable=False, default=50.0)
    fitting_price_conservatory: float = db.Column(db.Float, nullable=False, default=35.0)
    fitting_price_95mm: float = db.Column(db.Float, nullable=False, default=5.0)

class DefaultSettings(db.Model):
    __allow_unmapped__ = True
    id: int = db.Column(db.Integer, primary_key=True)
    plate_length: float = db.Column(db.Float, nullable=False, default=6000)  # mm
    length_95mm: float = db.Column(db.Float, nullable=False, default=200)   # mm
    cutting_allowance: float = db.Column(db.Float, nullable=False, default=2)  # mm
    
    # Material usage per meter
    hot_glue_per_meter: float = db.Column(db.Float, nullable=False, default=0.05)  # sticks/m
    glue_with_activator_per_meter: float = db.Column(db.Float, nullable=False, default=0.05)  # ml/bottle
    silicone_per_meter: float = db.Column(db.Float, nullable=False, default=0.1)  # ml/tube
    silicone_color_per_meter: float = db.Column(db.Float, nullable=False, default=0.1)  # ml/tube
    pvc_cleaner_per_meter: float = db.Column(db.Float, nullable=False, default=0.1)  # ml/bottle
    fixall_per_meter: float = db.Column(db.Float, nullable=False, default=0.1)  # ml/bottle
    glue_color_extra: float = db.Column(db.Float, nullable=False, default=0.05)  # ml/bottle extra for colored boards 