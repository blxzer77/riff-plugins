export function linkOrder(userId: string, orderId: string): string {
  return `/users/${userId}/orders/${orderId}`;
}
