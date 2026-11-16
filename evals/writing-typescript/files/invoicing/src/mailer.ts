export interface Outgoing {
  to: string;
  subject: string;
  body: string;
}

export const outbox: Outgoing[] = [];

/** Queue the invoice email. */
export function sendInvoice(to: string, customerName: string, amountCents: number): void {
  const amount = (amountCents / 100).toFixed(2);
  outbox.push({
    to,
    subject: `Your invoice: $${amount}`,
    body: `Dear ${customerName},\n\nYour invoice for $${amount} is attached.\n`,
  });
}
