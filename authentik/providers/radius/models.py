"""Radius Provider"""

from base64 import b64encode

from django.db import models
from django.http import HttpRequest
from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _
from pyrad.dictionary import Attribute, Dictionary
from pyrad.packet import AuthPacket
from rest_framework.serializers import Serializer

from authentik.core.models import Provider
from authentik.lib.generators import generate_id
from authentik.outposts.models import OutpostModel


class RadiusProvider(OutpostModel, Provider):
    """Allow applications to authenticate against authentik's users using Radius."""

    shared_secret = models.TextField(
        default=generate_id,
        help_text=_("Shared secret between clients and server to hash packets."),
    )

    client_networks = models.TextField(
        default="0.0.0.0/0, ::/0",
        help_text=_(
            "List of CIDRs (comma-separated) that clients can connect from. A more specific "
            "CIDR will match before a looser one. Clients connecting from a non-specified CIDR "
            "will be dropped."
        ),
    )

    mfa_support = models.BooleanField(
        default=True,
        verbose_name="MFA Support",
        help_text=_(
            "When enabled, code-based multi-factor authentication can be used by appending a "
            "semicolon and the TOTP code to the password. This should only be enabled if all "
            "users that will bind to this provider have a TOTP device configured, as otherwise "
            "a password may incorrectly be rejected if it contains a semicolon."
        ),
    )

    @property
    def launch_url(self) -> str | None:
        """Radius never has a launch URL"""
        return None

    @property
    def component(self) -> str:
        return "ak-provider-radius-form"

    @property
    def icon_url(self) -> str | None:
        return static("authentik/sources/radius.svg")

    @property
    def serializer(self) -> type[Serializer]:
        from authentik.providers.radius.api import RadiusProviderSerializer

        return RadiusProviderSerializer

    def get_attributes(self, request: HttpRequest) -> str:
        input = {
            "vendor_code": 9,
            "vendor_name": "Cisco",
            "attribute_name": "AVPair",
            "attribute_code": 1,
            "attribute_type": "string",
        }

        dict = Dictionary("authentik/providers/radius/dictionaries/dictionary")
        dict.vendors.Add(input["vendor_name"], input["vendor_code"])
        dict.attributes["Cisco-AVPair"] = Attribute(
            input["attribute_name"],
            input["attribute_code"],
            input["attribute_type"],
            vendor=input["vendor_name"],
        )

        p = AuthPacket()
        p.secret = self.shared_secret
        p.dict = dict
        p["Cisco-AVPair"] = "shell:priv-level=15"
        return b64encode(p.RequestPacket()).decode()

    def __str__(self):
        return f"Radius Provider {self.name}"

    class Meta:
        verbose_name = _("Radius Provider")
        verbose_name_plural = _("Radius Providers")
