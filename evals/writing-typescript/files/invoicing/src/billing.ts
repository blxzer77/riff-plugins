import { customerFromRow, type CustomerRow } from "./customers.ts";
import { sendInvoice } from "./mailer.ts";

export function billCustomer(row: CustomerRow, amountCents: number): void {
  const customer = customerFromRow(row);
  sendInvoice(customer.name, customer.email, amountCents);
}
