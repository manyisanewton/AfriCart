export interface UserTableRow {
  id: string;
  name: string;
  email: string;
  status: 'Active' | 'Suspended';
  role: string;
  joined: string;
  phone?: string;
  emailVerified?: boolean;
  roleValue?: string;
  isActive?: boolean;
  detail?: Record<string, any>;
  raw?: Record<string, any>;
}
