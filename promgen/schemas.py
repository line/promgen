from drf_spectacular.openapi import AutoSchema


class CustomSchema(AutoSchema):
    def is_excluded(self):
        return not self.path.startswith("/rest/v2/") or self.path.startswith("/rest/v2/schema/")
