# sample_project controllers — DELIBERATELY violates the arch model (fixture for the discriminating selftest).
from app.persistence.order_repo import OrderRepo   # layer rule + boundary breach: controllers must NOT reach persistence
from app.domain.order import OrderSpec             # allowed (controllers -> domain)


def place_order(customer_id, product_id, qty, coupon, region, channel):  # 6 params > max_params(5) → too_many_params
    repo = OrderRepo()
    spec = OrderSpec
    total = 0
    for i in range(qty):
        line = product_id * i
        total += line
        if line > 100:
            total -= 1
        elif line < 0:
            total += 1
        else:
            total += 0
    record = repo.save(customer_id, total)   # span > max_method_loc(10) → long_method
    return record
