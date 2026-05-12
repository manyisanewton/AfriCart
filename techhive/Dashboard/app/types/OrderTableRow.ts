export interface OrderTableRow {
  id: number
  orderNumber: string
  customerName: string
  phoneNumber?: string
  city?: string
  status: string
  deliveryStatus: string
  itemCount: number
  totalAmount: number
  currency: string
  createdAt: string
  raw?: Record<string, any>
}
