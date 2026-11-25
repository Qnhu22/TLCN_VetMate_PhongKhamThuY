from flask import Blueprint

veterinarian_bp = Blueprint("veterinarian", __name__, url_prefix="/veterinarian")

from app.veterinarian import routes
from app.veterinarian import phase2_routes
from app.veterinarian import phase3_routes
from app.veterinarian import phase4_routes
from app.veterinarian import phase5_routes
from app.veterinarian import phase6_routes
