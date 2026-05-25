export interface ProductTableRow {
  id: number;
  name: string;
  sku: string;
  price: number;
  currency?: string;
  status: string;
  category: string;
  stock: number;
  imageUrl?: string;
  updatedAt?: string;
  vendorName?: string;
  rating?: number | null;
  reviewCount?: number;
  isActive?: boolean;
  raw?: Record<string, any>;
}

export interface ProductStockData {
  date: string
  stock: number
}
