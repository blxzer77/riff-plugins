export interface Customer {
  id: string;
  name: string;
  email: string;
}

/** Row as it comes back from the customers table. */
export interface CustomerRow {
  id: string;
  full_name: string;
  email: string;
}

export function customerFromRow(row: CustomerRow): Customer {
  return { id: row.id, name: row.full_name, email: row.email.trim().toLowerCase() };
}
