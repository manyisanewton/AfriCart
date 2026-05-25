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
  trackingToken?: string
  notes?: string
  shippingAddress?: Record<string, any>
  refunds?: Array<Record<string, any>>
  items?: Array<Record<string, any>>
  deliveryAgent?: Record<string, any> | null
  raw?: Record<string, any>
}
