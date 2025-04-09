import logging
from odoo import models
from datetime import datetime, date

_logger = logging.getLogger(__name__)


class DueInvoiceReport(models.AbstractModel):
    _name = "report.due_invoice_report.report_due_invoice"
    _description = "Due Invoice Report"

    def _get_report_values(self, docids, data=None):
        docs = self.env["due.invoice.wizard"].browse(docids)
        company = self.env.company
        records = []
        for partner in docs.partner_id:
      #overpayments
      #search for all unreconciled payments
            counterpart_payment = self.env["account.payment"].search([
                    ("state", "=", "posted"),
                    ("payment_type", "=", "inbound"),
                    ("partner_type", "=", "customer"),
                    ("partner_id", "=", partner.id),
                    ("is_reconciled", "=", False),
                ])
            #look for those that don't have reconcile IDs
            for payment in counterpart_payment:
                    #skip those that do not
                    if not payment.reconciled_invoice_ids:
                        continue
                    else:  
                        #for those who have
                        for invoice in payment.reconciled_invoice_ids: 
                            #check if the payment amount is more than the invoice amount and the invoice amount is not zero[needed in order to filter unreconcile entries thate came up in estept 1]
                            if payment.amount > invoice.amount_total_signed and invoice.amount_total_signed !=0: 
                                    #find the remaining amount                      
                                    rem = payment.amount - invoice.amount_total_signed
                                    #create record in payment and ensure that the corresponding entry is note erased when payments are searched in line 112
                                    record = {
                                                        "date": payment.date,
                                                        "reference":  payment.name,
                                                        "due_date": payment.date,
                                                        "debit": 0.0,   
                                                        "credit": rem, 
                                                        "running_balance": 0.0,  
                                                    }

                                    if record not in records:
                                                        records.append(record)
                        

           
           #Invoices
            invoices = self.env["account.move"].search([
                ("partner_id", "=", partner.id),
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
 		        ("amount_residual", ">", 0),
                ("name", "not ilike", "STJ"),    
                ("line_ids.matched_debit_ids", "=", False),  
                ("line_ids.matched_credit_ids", "=", False) 
            ])

            for inv in invoices:
                
                record = {
                    "date": inv.invoice_date,
                    "reference": inv.name,
                    "due_date": inv.invoice_date_due,
                    "debit": inv.amount_residual,   # No debit for invoices
                    "credit": 0.0, 
                    "running_balance": inv.amount_residual,  
                }
           

                if record not in records:
                    records.append(record)
                    
            #Credit Notes
            cnotes = self.env["account.move"].search([
                ("partner_id", "=", partner.id),
                ("move_type", "=", "out_refund"),   
                ("payment_state", "!=", "paid"), 
                ("state", "=", "posted"),  
            ])
          
            for cred in cnotes:
                record = {
                    "date":cred.invoice_date,
                    "reference": cred.name,
                    "due_date": cred.invoice_date_due,
                    "debit": 0.0,    
                    "credit": cred.amount_residual,
                    "running_balance": 0.0,  
                }
                

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

          

            for pmt in account_payments:
                if not any(rec["reference"] == pmt.move_id.name for rec in records):
                    record = {
                        "date": pmt.date,
                        "reference": pmt.move_id.name,
                        "due_date": pmt.date,
                        "debit": 0.0,
                        "credit": pmt.amount_total_signed,
                        "running_balance": 0.0
                    }
                    records.append(record)

            #Special Credit Notes

            special_credit = self.env["account.move"].search([
                ("partner_id", "=", partner.id),
                ("state", "=", "posted"), 
                ("move_type", "=", "entry"), 
                ("name", "ilike", "SRInv"), 
            ])

           # _logger.info("Found %d payments for partner %s", len(payments), partner.name)

            for spec_credit in special_credit:
                record = {
                    "date": spec_credit.date,
                    "reference": spec_credit.name,
                    "due_date": spec_credit.date,
                    "debit": 0.0,  # Payment as Debit
                    "credit": spec_credit.amount_total_signed, 
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
                    "due_date": pmtmv.date,
                    "debit": 0.0,  # Payment as Debit
                    "credit": pmtmv.amount_total_signed, 
                    "running_balance": 0.0
                }
                _logger.debug("Generated record for payment: %s", record)
                if record not in records:
                    records.append(record)
            #Journal Entries
            #Journal entries have no field relating to partner in the form view so we create one with studio
            #Set this field to be visible only if the journal_id is miscellaneous and editable if state is not posted

            jrnlentries = self.env["account.move"].search([
                ("x_studio_customer_2", "=", partner.id),
                ("move_type", "=", "entry"),
		        ("name", "not ilike", "STJ"),  
                ("journal_id", "=", 3),  
            ])
            #_logger.info("Found %d Journal Entries for partner %s", len(jrnlentries), partner.name)

            for entry in jrnlentries:
                record = {
                    "date": entry.date,
                    "reference": entry.name,
                    "due_date": entry.date,
                    "debit": 0.0,  # Payment as Debit
                    "credit": entry.amount_total_signed, 
                    "running_balance": 0.0
                }
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
                    "due_date": pmtstk.date,
                    "debit": 0.0,  # Payment as Debit
                    "credit": pmtstk.amount_total_signed, 
                    "running_balance": 0.0
                }
                _logger.debug("Generated record for payment: %s", record)
                if record not in records:
                    records.append(record)
        
        for record in records:
            record.setdefault('debit', 0.0)  
            record.setdefault('credit', 0.0)  
            record.setdefault('date', '')  
            record.setdefault('reference', '')  
            record.setdefault('running_balance', 0.0)

        # Final record that will be returned
        docs_sorted = sorted(records, key=lambda x: x['date'])

        def group_by_date(docs_sorted):
            today = date.today()
            sums = {
                "AtDate": 0,
                "30days": 0,
                "60days": 0,
                "90days": 0,
                "120days": 0,
                "Over120": 0,
            }

            for record in docs_sorted:
                raw_date = record.get("due_date")
                debit = record.get("debit", 0.0)
                credit = record.get("credit", 0.0)
                running_balance = debit-credit

                # Convert string dates to date objects if necessary
                if isinstance(raw_date, str):
                    try:
                        record_date = datetime.strptime(raw_date, "%Y-%m-%d").date()  # Adjust format as needed
                    except ValueError:
                        continue  # Skip invalid date formats
                elif isinstance(raw_date, datetime):
                    record_date = raw_date.date()  # Convert datetime to date
                elif isinstance(raw_date, date):
                    record_date = raw_date  # Already a date object
                else:
                    continue  # Skip invalid types

                # Calculate days difference
                delta_days = (today - record_date).days
                if delta_days <= 0:
                    sums["AtDate"] += running_balance 
                elif 1 <= delta_days < 31:
                    sums["30days"] += running_balance
                elif 31 <= delta_days < 61:
                    sums["60days"] += running_balance
                elif 61 <= delta_days < 91:
                    sums["90days"] += running_balance
                elif 91 <= delta_days < 121:
                    sums["120days"] += running_balance
                else:
                    sums["Over120"] += running_balance 


            _logger.info("Grouped by date: %s", sums)
            return sums

             


        final_report_values = {
            "doc_ids": docids,
            "doc_model": "due.invoice.wizard",
            "docs": docs,
            "company": company,
            "records": docs_sorted,     
            "grouped_sums": group_by_date(docs_sorted),  # Include grouped sums
    
        }
       
        

        return final_report_values
