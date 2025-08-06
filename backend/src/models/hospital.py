from flask_sqlalchemy import SQLAlchemy
from src.models.user import db

class Hospital(db.Model):
    __tablename__ = 'hospitals'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    level = db.Column(db.String(10))  # 三甲、三乙等
    address = db.Column(db.Text)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    phone = db.Column(db.String(20))
    website = db.Column(db.String(200))
    specialties = db.Column(db.Text)  # JSON string of specialties
    rating = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'level': self.level,
            'address': self.address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'phone': self.phone,
            'website': self.website,
            'specialties': self.specialties,
            'rating': self.rating,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    specialties = db.Column(db.Text)  # JSON string of specialties
    
    hospital = db.relationship('Hospital', backref=db.backref('departments', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'hospital_id': self.hospital_id,
            'name': self.name,
            'description': self.description,
            'specialties': self.specialties
        }

class SearchHistory(db.Model):
    __tablename__ = 'search_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)  # 移除外键约束，允许匿名用户
    symptoms = db.Column(db.Text)  # JSON string of symptoms
    location_lat = db.Column(db.Float)
    location_lng = db.Column(db.Float)
    search_time = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'symptoms': self.symptoms,
            'location_lat': self.location_lat,
            'location_lng': self.location_lng,
            'search_time': self.search_time.isoformat() if self.search_time else None
        }

