# sample_project workflow — one reverse-dependency boundary breach (workflow -> controllers is not whitelisted).
from app.persistence.order_repo import OrderRepo            # allowed (workflow -> persistence)
from app.controllers.order_controller import place_order    # boundary breach: workflow -> controllers not in allowed_dependencies
from app.domain.order import OrderSpec                        # allowed (workflow -> domain)


def run(customer_id, product_id):
    _ = OrderRepo
    _ = OrderSpec
    return place_order(customer_id, product_id, 1, None, "us", "web")
