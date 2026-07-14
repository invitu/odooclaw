import uuid
from datetime import timedelta
from odoo import models, fields, api


class MailOdooClawSessionToken(models.Model):
    _name = "mail.odooclaw.session.token"
    _description = "OdooClaw Session Token"
    _rec_name = "token"

    token = fields.Char(required=True, index=True, readonly=True)
    model = fields.Char(required=True, readonly=True)
    res_id = fields.Integer(required=True, readonly=True)
    expiry = fields.Datetime(required=True)

    @api.model
    def _get_or_create(self, model, res_id):
        """
        Get existing valid session token for (model, res_id) or create a new one.
        The TTL is sliding — refreshed on each use.
        """
        ttl = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("odooclaw.session_token_ttl", "1800")
        )
        now = fields.Datetime.now()
        record = self.sudo().search(
            [
                ("model", "=", model),
                ("res_id", "=", res_id),
                ("expiry", ">", now),
            ],
            limit=1,
        )
        if record:
            record.expiry = now + timedelta(seconds=ttl)
            return record
        return self.sudo().create({
            "token": str(uuid.uuid4()),
            "model": model,
            "res_id": res_id,
            "expiry": now + timedelta(seconds=ttl),
        })

    @api.model
    def _validate(self, token_str, model, res_id):
        """
        Validate a session token and refresh its TTL (sliding window).
        Returns the token record if valid (truthy), empty recordset otherwise (falsy).
        """
        ttl = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("odooclaw.session_token_ttl", "1800")
        )
        record = self.sudo().search(
            [
                ("token", "=", token_str),
                ("expiry", ">", fields.Datetime.now()),
                ("model", "=", model),
                ("res_id", "=", res_id),
            ],
            limit=1,
        )
        if record:
            record.expiry = fields.Datetime.now() + timedelta(seconds=ttl)
        return record

    @api.model
    def _cleanup_expired(self):
        """Cron: remove expired session tokens."""
        self.sudo().search(
            [("expiry", "<", fields.Datetime.now())]
        ).unlink()
