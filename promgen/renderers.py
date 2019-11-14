import yaml
from rest_framework import renderers


# https://www.django-rest-framework.org/api-guide/renderers/#custom-renderers
class RuleRenderer(renderers.BaseRenderer):
    format = "yaml"
    media_type = "application/x-yaml"
    charset = "utf-8"

    def render(self, data, media_type=None, renderer_context=None):
        # If this is a 'real' request, then we'll add a header so
        # that we get a friendly name with our downloaded file
        if renderer_context and "response" in renderer_context:
            renderer_context["response"][
                "Content-Disposition"
            ] = "attachment; filename=promgen.rule.yml"

        return yaml.safe_dump(
            {"groups": [{"name": name, "rules": data[name]} for name in data]},
            default_flow_style=False,
            allow_unicode=True,
            encoding=self.charset,
        )
