from odoo import models, fields, api
import base64

class DueInvoiceWizard(models.TransientModel):
    _name = "due.invoice.wizard"
    _description = "Print Due Invoices"

    partner_id = fields.Many2one("res.partner", string="Customer", required=True, domain=[("customer_rank", ">", 0)])

    def action_print_due_invoices(self):
        return self.env.ref("due_invoice_report.action_due_invoice_report").report_action(self)

    def send_report_email(self):
        """Generates the Due Invoice report and sends it via email."""
        self.ensure_one()

        if not self.partner_id.email:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error",
                    "message": "Customer has no email address. Please update their contact details.",
                    "type": "danger",
                    "sticky": False,
                },
            }

        report_name = "due_invoice_report.report_due_invoice_action"
        pdf_content, _ = self.env["ir.actions.report"]._render_qweb_pdf(report_name, [self.id])
        pdf_base64 = base64.b64encode(pdf_content)


        attachment = self.env["ir.attachment"].create({
            "name": f"Due_Invoices_{self.partner_id.name}.pdf",
            "type": "binary",
            "datas": pdf_base64,
            "res_model": "due.invoice.wizard",
            "res_id": self.id,
            "mimetype": "application/pdf",
        })

        mail_template = self.env.ref("due_invoice_report.email_template_due_invoices")
        if not mail_template:
            raise ValueError("Email template not found.")
        
        mail_values = {
            "attachment_ids": [(4, attachment.id)],
            "email_to": self.partner_id.email,
        }

        mail_template.send_mail(self.id, force_send=True, email_values=mail_values)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Success",
                "message": "Email Successfully Sent",
                "type": "success",
                "sticky": False,
                "next": {
                    "type": "ir.actions.client",
                    "tag": "reload",
                },
            },
    }
       
