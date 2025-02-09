import logging
from odoo import models

_logger = logging.getLogger(__name__)

class DueInvoiceReport(models.AbstractModel):
    _name = "report.due_invoice_report.report_due_invoice"
    _description = "Due Invoice Report"

    def _get_report_values(self, docids, data=None):
        _logger.info("Generating Due Invoice Report for docids: %s", docids)

        docs = self.env["due.invoice.wizard"].browse(docids)
        company = self.env.company
        records = []

        for partner in docs.partner_id:
            _logger.info("Processing partner: %s (ID: %s)", partner.name, partner.id)

           #Invoices
            invoices = self.env["account.move"].search([
                ("partner_id", "=", partner.id),
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
 		        ("amount_residual", ">", 0),
                ("name", "not ilike", "STJ"),  
                ("reversal_move_id", "=", False),  
                ("line_ids.matched_debit_ids", "=", False),  
                ("line_ids.matched_credit_ids", "=", False) 
            ])


            _logger.info("Found %d invoices for partner %s", len(invoices), partner.name)

            for inv in invoices:
                record = {
                    "date": inv.invoice_date,
                    "reference": inv.name,
                    "due_date": inv.invoice_date_due,
                    "debit": inv.amount_residual,   # No debit for invoices
                    "credit": 0.0, 
                    "running_balance": inv.amount_residual,  
                }
                _logger.debug("Generated record for invoice: %s", record)

                if record not in records:
                    records.append(record)
            #Credit Notes
            cnotes = self.env["account.move"].search([
                ("partner_id", "=", partner.id),
                ("move_type", "=", "out_refund"),   
                ("payment_state", "!=", "paid"),   
            ])
            _logger.info("Found %d Credit Notes for partner %s", len(cnotes), partner.name)
            for cred in cnotes:
                record = {
                    "date":cred.invoice_date,
                    "reference": cred.name,
                    "due_date": cred.invoice_date_due,
                    "debit": 0.0,    
                    "credit": cred.amount_residual,
                    "running_balance": 0.0,  
                }
                _logger.debug("Generated record for invoice: %s", record)

                if record not in records:
                    records.append(record)


            # Fetch payments in account payment
            account_payments = self.env["account.payment"].search([
                ("partner_id", "=", partner.id),
                ("state", "=", "posted"), 
                ("move_type", "=", "entry"),
                ("is_reconciled", "=", False),
                ("payment_state", "!=", "paid"), 
            ])

           # _logger.info("Found %d payments for partner %s", len(payments), partner.name)

            for pmt in account_payments:
                record = {
                    "date": pmt.date,
                    "reference": pmt.move_id.name,
                    "due_date": "-",
                    "debit": 0.0,  # Payment as Debit
                    "credit": pmt.amount_total_signed, 
                    "running_balance": 0.0
                }
                _logger.debug("Generated record for payment: %s", record)

                if record not in records:
                    records.append(record)

            #Special Credit Notes

            special_credit = self.env["account.move"].search([
                ("partner_id", "=", partner.id),
                ("state", "=", "posted"), 
                ("move_type", "=", "entry"), 
                ("name", "ilike", "SRInv"), 
                ("has_reconciled_entries", "=", False),
            ])

           # _logger.info("Found %d payments for partner %s", len(payments), partner.name)

            for spec_credit in special_credit:
                record = {
                    "date": spec_credit.date,
                    "reference": spec_credit.name,
                    "due_date": "-",
                    "debit": spec_credit.amount_total_signed,  # Payment as Debit
                    "credit": 0.0, 
                    "running_balance": 0.0
                }

                if record not in records:
                    records.append(record)
            #Payments in account move

            paymentsmv = self.env["account.move"].search([
                ("partner_id", "=", partner.id),
                ("move_type", "=", "entry"),
		        ("name", "not ilike", "STJ"), 
                ("payment_state", "=", "not_paid"),  
                ("state", "=", "posted"),  
            ])
            filtered_payments = paymentsmv.filtered(lambda m: hasattr(m, "amount"))
           # _logger.info("Found %d payments for partner %s", len(payments), partner.name)

            for pmtmv in filtered_payments:
                record = {
                    "date": pmtmv.date,
                    "reference": pmtmv.name,
                    "due_date": "-",
                    "debit": 0.0,  # Payment as Debit
                    "credit": pmtmv.amount_total_signed, 
                    "running_balance": 0.0
                }
                _logger.debug("Generated record for payment: %s", record)
                if record not in records:
                    records.append(record)

            paymentstk = self.env["account.move"].search([
                ("partner_id", "=", partner.id),
                ("move_type", "=", "entry"),
                ("name", "not ilike", "STJ"), 
                ("line_ids.full_reconcile_id", "=", False),  
                ("state", "=", "posted"),   
            ])        
            
            filtered_payments_2 = paymentstk.filtered(lambda m: hasattr(m, "amount"))
           # _logger.info("Found %d special payments for partner %s", len(payments), partner.name)

            for pmtstk in filtered_payments_2:
                record = {
                    "date": pmtstk.date,
                    "reference": pmtstk.name,
                    "due_date": "-",
                    "debit": 0.0,  # Payment as Debit
                    "credit": pmtstk.amount_total_signed, 
                    "running_balance": 0.0
                }
                _logger.debug("Generated record for payment: %s", record)
                if record not in records:
                    records.append(record)
	    
        _logger.info("Total records generated: %d", len(records))
        _logger.debug("All generated records: %s", records)

        for record in records:
            record.setdefault('debit', 0.0)  
            record.setdefault('credit', 0.0)  
            record.setdefault('date', '')  
            record.setdefault('reference', '')  
            record.setdefault('running_balance', 0.0)

        # Final record that will be returned
        docs_sorted = sorted(records, key=lambda x: x['date'])
        final_report_values = {
            "doc_ids": docids,
            "doc_model": "due.invoice.wizard",
            "docs": docs,
            "company": company,
            "records": docs_sorted,  
        }
        _logger.info("Final report data being returned: %s", final_report_values)
        

        return final_report_values
