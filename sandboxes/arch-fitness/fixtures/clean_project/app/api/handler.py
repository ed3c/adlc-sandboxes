# clean_project — conforms to its arch model: api -> core only, no smells. measure() must verdict PASS.
from app.core.service import Service


class Handler:
    def handle(self, req):
        return Service().run(req)
