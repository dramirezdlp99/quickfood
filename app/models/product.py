from ..extensions import db


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    price = db.Column(db.Integer, nullable=False)  # pesos colombianos, sin decimales
    image = db.Column(db.String(255), nullable=True)

    restaurant = db.relationship("Restaurant", back_populates="products")

    def __repr__(self) -> str:
        return f"<Product {self.name} ${self.price}>"
