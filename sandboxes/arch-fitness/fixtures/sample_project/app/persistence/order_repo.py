# sample_project persistence — a Large Class + a Zone-of-Pain coupling demonstrator.
# Concrete (no abstraction), depended-on by controllers AND workflow (Ca=2), depends on domain (Ce=1)
# → I≈0.33, A=0, D=|0+0.33-1|≈0.67 > max_distance(0.5): instable enough to be hard to reuse, abstract enough = no.
from app.domain.order import OrderSpec   # allowed (persistence -> domain)


class OrderRepo:                          # 7 methods > max_class_methods(5) → large_class
    def save(self, customer_id, total):
        return (customer_id, total)

    def load(self, oid):
        return oid

    def delete(self, oid):
        return None

    def update(self, oid, total):
        return (oid, total)

    def list_all(self):
        return []

    def count(self):
        return 0

    def purge(self):
        _ = OrderSpec
        return None
