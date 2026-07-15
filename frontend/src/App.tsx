import React, { useState, useEffect } from 'react';
import { 
  Shield, FileText, Users, Activity, LogOut, 
  Plus, MapPin, Truck, AlertTriangle, CheckCircle, 
  Upload, ShieldAlert, BookOpen, Clock, User,
  Eye, EyeOff
} from 'lucide-react';

const getApiBase = () => {
  let url = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
  
  // Automatic fallback: If deployed on Vercel but the API URL points to localhost, self, or the example URL,
  // override it to point directly to the live Render backend.
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost') {
    if (url.includes('localhost') || url.includes(window.location.hostname) || url.includes('loadflow-api.onrender.com')) {
      url = 'https://loadflow-operations-suite.onrender.com/api';
    }
  }
  
  return url.endsWith('/api') || url.endsWith('/api/') ? url : `${url.replace(/\/$/, '')}/api`;
};
const API_BASE = getApiBase();

// Helper types
interface Organization {
  id: number;
  name: string;
  type: string;
}

interface UserProfile {
  id: number;
  name: string;
  email: string;
  account_type: string;
  org_id?: number;
  role_id?: number;
  org?: Organization;
  permissions: string[];
}

interface Load {
  id: number;
  title: string;
  origin: string;
  destination: string;
  equipment_required: string;
  commodity_type: string;
  status: string;
  compliance_flag: boolean;
  shipper_id: number;
  broker_id: number;
  carrier_id?: number;
  pod_url?: string;
  created_at: string;
}

interface Permission {
  id: number;
  permission_name: string;
}

interface Role {
  id: number;
  role_name: string;
}

interface ComplianceRecord {
  id: number;
  carrier_id: number;
  insurance_expiry?: string;
  authority_status: string;
  approved_equipment: string[];
  approved_commodities: string[];
}

interface RateConfirmation {
  id: number;
  load_id: number;
  version: number;
  rate: number;
  accessorials: number;
  confirmed_by?: number;
  confirmed_at?: string;
}

interface AuditLog {
  id: number;
  user_email?: string;
  action: string;
  target_type?: string;
  target_id?: string;
  old_value?: string;
  new_value?: string;
  details?: string;
  created_at: string;
}

export default function App() {
  // Auth state
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  
  // Navigation
  const [currentTab, setCurrentTab] = useState<string>('loads');
  const [isLogin, setIsLogin] = useState<boolean>(true);
  
  // Registration form
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regAccountType, setRegAccountType] = useState('broker');
  const [regOrgName, setRegOrgName] = useState('');

  // Login form
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Data collections
  const [loads, setLoads] = useState<Load[]>([]);
  const [selectedLoad, setSelectedLoad] = useState<Load | null>(null);
  const [carriers, setCarriers] = useState<Organization[]>([]);
  const [shippers, setShippers] = useState<UserProfile[]>([]);
  const [permissionsCatalog, setPermissionsCatalog] = useState<Permission[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [staff, setStaff] = useState<UserProfile[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [complianceMap, setComplianceMap] = useState<Record<number, ComplianceRecord>>({});
  const [ratesMap, setRatesMap] = useState<Record<number, RateConfirmation[]>>({});

  // Modals / Dropdowns / Wizards
  const [showCreateLoad, setShowCreateLoad] = useState(false);
  const [showCreateStaff, setShowCreateStaff] = useState(false);
  const [showCreateRole, setShowCreateRole] = useState(false);
  
  // Creation form states
  const [newLoadTitle, setNewLoadTitle] = useState('');
  const [newLoadOrigin, setNewLoadOrigin] = useState('');
  const [newLoadDest, setNewLoadDest] = useState('');
  const [newLoadEq, setNewLoadEq] = useState('Reefer');
  const [newLoadComm, setNewLoadComm] = useState('Food');
  const [newLoadShipperId, setNewLoadShipperId] = useState<number | null>(null);

  const [newStaffName, setNewStaffName] = useState('');
  const [newStaffEmail, setNewStaffEmail] = useState('');
  const [newStaffPassword, setNewStaffPassword] = useState('');
  const [newStaffRoleId, setNewStaffRoleId] = useState<number | null>(null);

  const [newRoleName, setNewRoleName] = useState('');
  const [newRolePerms, setNewRolePerms] = useState<number[]>([]);

  const [assignCarrierId, setAssignCarrierId] = useState<number | null>(null);
  const [rateAmount, setRateAmount] = useState<number>(0);
  const [accessorialsAmount, setAccessorialsAmount] = useState<number>(0);
  const [podBase64, setPodBase64] = useState<string>('');

  // Carrier compliance edit state
  const [compInsuranceExpiry, setCompInsuranceExpiry] = useState('');
  const [compAuthority, setCompAuthority] = useState('Active');
  const [compEquipment, setCompEquipment] = useState<string[]>([]);
  const [compCommodities, setCompCommodities] = useState<string[]>([]);

  // Toast notifications
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'warning' } | null>(null);
  const [serverStatus, setServerStatus] = useState<'checking' | 'online' | 'waking'>('checking');
  const [showPassword, setShowPassword] = useState(false);

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Ping server on mount to wake up Render free tier from cold start
  useEffect(() => {
    const pingServer = async () => {
      try {
        const res = await fetch(`${API_BASE.replace('/api', '')}`, { method: 'GET' });
        if (res.ok || res.status === 405) {
          setServerStatus('online');
        } else {
          setServerStatus('waking');
          // Retry after 5s
          setTimeout(pingServer, 5000);
        }
      } catch {
        setServerStatus('waking');
        setTimeout(pingServer, 5000);
      }
    };
    pingServer();
  }, []);

  // API Call helper
  const apiCall = async (endpoint: string, options: RequestInit = {}) => {
    const headers = new Headers(options.headers || {});
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    let res: Response;
    try {
      res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    } catch {
      throw new Error('Cannot reach server — it may be starting up. Please wait 30 seconds and try again.');
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({
        detail: `Server returned ${res.status}. If this is your first request, the server may be waking up — please wait 30 seconds and try again.`
      }));
      throw new Error(err.detail || 'Request failed');
    }

    return res.json();
  };

  // Fetch current user details
  const fetchCurrentUser = async () => {
    try {
      const user = await apiCall('/auth/me');
      setCurrentUser(user);
      if (user.account_type === 'broker') {
        setCurrentTab('loads');
      } else if (user.account_type === 'carrier') {
        setCurrentTab('loads');
      } else {
        setCurrentTab('loads');
      }
    } catch (err: any) {
      handleLogout();
    }
  };

  // Load initial data
  useEffect(() => {
    if (token) {
      fetchCurrentUser();
    }
  }, [token]);

  // Secondary data loader based on tabs and roles
  useEffect(() => {
    if (!currentUser) return;

    if (currentTab === 'loads') {
      loadLoads();
      if (currentUser.account_type === 'broker') {
        loadCarriers();
        loadShippers();
      }
    } else if (currentTab === 'staff' || currentTab === 'roles') {
      if (currentUser.permissions.includes('staff.manage')) {
        loadStaff();
        loadRoles();
        loadPermissionsCatalog();
      }
    } else if (currentTab === 'compliance') {
      if (currentUser.account_type === 'carrier') {
        loadCarrierCompliance(currentUser.org_id!);
      }
    } else if (currentTab === 'logs') {
      loadAuditLogs();
    }
  }, [currentUser, currentTab]);

  const loadLoads = async () => {
    try {
      const data = await apiCall('/loads');
      setLoads(data);
      // Fetch latest rates for each load
      data.forEach((l: Load) => {
        loadRatesForLoad(l.id);
      });
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  const loadRatesForLoad = async (loadId: number) => {
    try {
      const res = await fetch(`${API_BASE}/rates/load/${loadId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      // The API doesn't have a direct get all rates route in the spec, but we can query them or catch empty
      if (res.ok) {
        const rate = await res.json();
        setRatesMap(prev => ({ ...prev, [loadId]: [rate] }));
      }
    } catch (e) {}
  };

  const loadCarriers = async () => {
    try {
      const data = await apiCall('/rbac/carriers');
      setCarriers(data);
    } catch (e) {}
  };

  const loadShippers = async () => {
    try {
      const data = await apiCall('/rbac/shippers');
      setShippers(data);
    } catch (e) {}
  };

  const loadStaff = async () => {
    try {
      const data = await apiCall('/rbac/staff');
      setStaff(data);
    } catch (e) {}
  };

  const loadRoles = async () => {
    try {
      const data = await apiCall('/rbac/roles');
      setRoles(data);
    } catch (e) {}
  };

  const loadPermissionsCatalog = async () => {
    try {
      const data = await apiCall('/rbac/permissions');
      setPermissionsCatalog(data);
    } catch (e) {}
  };

  const loadCarrierCompliance = async (carrierId: number) => {
    try {
      const data = await apiCall(`/compliance/carrier/${carrierId}`);
      setComplianceMap(prev => ({ ...prev, [carrierId]: data }));
      
      // Populate form state if it's the current user's org
      if (currentUser?.org_id === carrierId) {
        setCompInsuranceExpiry(data.insurance_expiry || '');
        setCompAuthority(data.authority_status || 'Active');
        setCompEquipment(data.approved_equipment || []);
        setCompCommodities(data.approved_commodities || []);
      }
    } catch (e) {}
  };

  const loadAuditLogs = async () => {
    try {
      const data = await apiCall('/logs');
      setAuditLogs(data);
    } catch (e) {}
  };

  // Auth operations
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    try {
      const body: any = {
        name: regName,
        email: regEmail,
        password: regPassword,
        account_type: regAccountType
      };
      if (regAccountType !== 'shipper') {
        body.org_name = regOrgName;
      }
      
      await apiCall('/auth/register', {
        method: 'POST',
        body: JSON.stringify(body)
      });

      showToast('Registration successful! Please login.', 'success');
      setIsLogin(true);
    } catch (err: any) {
      setAuthError(err.message);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    try {
      const data = await apiCall('/auth/login', {
        method: 'POST',
        body: JSON.stringify({
          email: loginEmail,
          password: loginPassword
        })
      });

      localStorage.setItem('token', data.access_token);
      setToken(data.access_token);
      showToast('Login successful', 'success');
    } catch (err: any) {
      setAuthError(err.message);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setCurrentUser(null);
    setLoads([]);
    setSelectedLoad(null);
    showToast('Logged out successfully', 'success');
  };

  // Business operations
  const handleCreateLoad = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiCall('/loads', {
        method: 'POST',
        body: JSON.stringify({
          title: newLoadTitle,
          origin: newLoadOrigin,
          destination: newLoadDest,
          equipment_required: newLoadEq,
          commodity_type: newLoadComm,
          shipper_id: Number(newLoadShipperId)
        })
      });
      showToast('Load created successfully');
      setShowCreateLoad(false);
      loadLoads();
      // Reset form
      setNewLoadTitle('');
      setNewLoadOrigin('');
      setNewLoadDest('');
      setNewLoadShipperId(null);
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  const handleAssignCarrier = async (loadId: number) => {
    if (!assignCarrierId) return;
    try {
      const updated = await apiCall(`/loads/${loadId}/assign`, {
        method: 'POST',
        body: JSON.stringify({
          carrier_id: Number(assignCarrierId)
        })
      });
      showToast('Carrier assigned successfully. Compliance validation checks complete.');
      setSelectedLoad(updated);
      loadLoads();
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  const handleCreateStaff = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiCall('/rbac/staff', {
        method: 'POST',
        body: JSON.stringify({
          name: newStaffName,
          email: newStaffEmail,
          password: newStaffPassword,
          role_id: Number(newStaffRoleId)
        })
      });
      showToast('Staff member added successfully');
      setShowCreateStaff(false);
      loadStaff();
      // Reset form
      setNewStaffName('');
      setNewStaffEmail('');
      setNewStaffPassword('');
      setNewStaffRoleId(null);
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  const handleCreateRole = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiCall('/rbac/roles', {
        method: 'POST',
        body: JSON.stringify({
          role_name: newRoleName,
          permission_ids: newRolePerms
        })
      });
      showToast('Custom role created successfully');
      setShowCreateRole(false);
      loadRoles();
      // Reset form
      setNewRoleName('');
      setNewRolePerms([]);
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  const handleUpdateCompliance = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiCall(`/compliance/carrier/${currentUser?.org_id}`, {
        method: 'PUT',
        body: JSON.stringify({
          insurance_expiry: compInsuranceExpiry,
          authority_status: compAuthority,
          approved_equipment: compEquipment,
          approved_commodities: compCommodities
        })
      });
      showToast('Compliance credentials updated successfully');
      loadCarrierCompliance(currentUser?.org_id!);
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  const handleProposeRate = async (loadId: number) => {
    try {
      const rateObj = await apiCall(`/rates/load/${loadId}`, {
        method: 'POST',
        body: JSON.stringify({
          rate: Number(rateAmount),
          accessorials: Number(accessorialsAmount)
        })
      });
      showToast('Rate proposal proposed successfully');
      setRatesMap(prev => ({ ...prev, [loadId]: [rateObj] }));
      loadLoads();
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  const handleConfirmRate = async (loadId: number, version: number) => {
    try {
      await apiCall(`/rates/load/${loadId}/confirm/${version}`, {
        method: 'POST'
      });
      showToast('Rate agreement signed! Load transitioned to Rate Confirmed.', 'success');
      loadRatesForLoad(loadId);
      loadLoads();
      // Refresh active load details
      const updated = await apiCall(`/loads/${loadId}`);
      setSelectedLoad(updated);
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  const handleUploadPod = async (loadId: number) => {
    if (!podBase64) return;
    try {
      const updated = await apiCall(`/loads/${loadId}/pod`, {
        method: 'POST',
        body: JSON.stringify({
          pod_data: podBase64
        })
      });
      showToast('Proof of Delivery (POD) document uploaded.', 'success');
      setSelectedLoad(updated);
      loadLoads();
      setPodBase64('');
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  const handleAdvanceStatus = async (loadId: number, targetStatus: string) => {
    try {
      const updated = await apiCall(`/loads/${loadId}/status`, {
        method: 'POST',
        body: JSON.stringify({
          status: targetStatus
        })
      });
      showToast(`Status updated to ${targetStatus}`);
      setSelectedLoad(updated);
      loadLoads();
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  // Helper toggle for lists
  const handleTogglePerm = (permId: number) => {
    if (newRolePerms.includes(permId)) {
      setNewRolePerms(newRolePerms.filter(id => id !== permId));
    } else {
      setNewRolePerms([...newRolePerms, permId]);
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'Posted': return 'badge-posted';
      case 'Carrier Assigned': return 'badge-assigned';
      case 'Rate Confirmed': return 'badge-confirmed';
      case 'Dispatched': return 'badge-dispatched';
      case 'In Transit': return 'badge-transit';
      case 'Delivered': return 'badge-delivered';
      case 'POD Verified': return 'badge-verified';
      case 'Closed': return 'badge-closed';
      default: return 'badge-posted';
    }
  };

  const getStatusFlowIndex = (status: string) => {
    const STATUS_FLOW = ["Posted", "Carrier Assigned", "Rate Confirmed", "Dispatched", "In Transit", "Delivered", "POD Verified", "Closed"];
    return STATUS_FLOW.indexOf(status);
  };

  // RENDER APP
  return (
    <div style={{ position: 'relative', minHeight: '100vh' }}>
      
      {/* Toast popup */}
      {toast && (
        <div style={{
          position: 'fixed',
          top: '24px',
          right: '24px',
          padding: '16px 24px',
          borderRadius: '8px',
          zIndex: 9999,
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          boxShadow: '0 8px 30px rgba(0,0,0,0.5)',
          background: toast.type === 'success' ? 'rgba(16, 185, 129, 0.95)' : 'rgba(239, 68, 68, 0.95)',
          color: '#fff',
          fontFamily: 'var(--font-title)',
          fontWeight: 600,
          animation: 'slideInRight 0.3s ease-out'
        }}>
          {toast.type === 'success' ? <CheckCircle size={20} /> : <AlertTriangle size={20} />}
          <span>{toast.message}</span>
        </div>
      )}

      {!token ? (
        /* Login / Signup Screen */
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          background: 'radial-gradient(circle at top right, rgba(124, 58, 237, 0.12), transparent), hsl(var(--bg-main))',
          padding: '20px'
        }}>
          <div className="glass-panel animate-fade-in" style={{
            width: '100%',
            maxWidth: '480px',
            padding: '40px',
            boxShadow: '0 24px 60px rgba(0,0,0,0.7)'
          }}>
            <div style={{ textAlign: 'center', marginBottom: '32px' }}>
              <div style={{ 
                display: 'inline-flex', 
                padding: '12px', 
                borderRadius: '16px', 
                background: 'rgba(124, 58, 237, 0.15)',
                color: 'hsl(var(--primary))',
                marginBottom: '16px',
                border: '1px solid rgba(124, 58, 237, 0.25)'
              }}>
                <Truck size={36} />
              </div>
              <h2 style={{ fontSize: '28px', color: '#fff', marginBottom: '8px' }}>LoadFlow Suite</h2>
              <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '15px' }}>
                {isLogin ? 'Freight brokerage and compliance management' : 'Onboard your organization and team'}
              </p>
            </div>

            {serverStatus === 'waking' && (
              <div style={{ background: 'rgba(234,179,8,0.1)', border: '1px solid rgba(234,179,8,0.3)', padding: '10px 16px', borderRadius: '8px', color: '#fde047', fontSize: '13px', marginBottom: '16px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>⚡</span><span>Server waking up (free tier)...</span>
                </div>
              </div>
            )}

            {authError && (
              <div style={{
                background: 'rgba(244, 63, 94, 0.1)',
                border: '1px solid rgba(244, 63, 94, 0.3)',
                padding: '12px 16px',
                borderRadius: '8px',
                color: '#fb7185',
                fontSize: '14px',
                marginBottom: '24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <AlertTriangle size={18} />
                  <span>{authError}</span>
                </div>
                <div style={{ fontSize: '12px', opacity: 0.8, borderTop: '1px solid rgba(244,63,94,0.2)', paddingTop: '8px', wordBreak: 'break-all' }}>
                  Attempted endpoint: <strong>{API_BASE}/auth/login</strong>
                </div>
              </div>
            )}

            {isLogin ? (
              <form onSubmit={handleLogin}>
                <div className="input-group">
                  <label className="input-label">Email Address</label>
                  <input 
                    type="email" 
                    required 
                    className="input-field" 
                    placeholder="name@organization.com"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                  />
                </div>
                <div className="input-group" style={{ marginBottom: '28px' }}>
                  <label className="input-label">Password</label>
                  <div style={{ position: 'relative' }}>
                    <input 
                      type={showPassword ? "text" : "password"} 
                      required 
                      className="input-field" 
                      placeholder="••••••••"
                      style={{ paddingRight: '40px' }}
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      style={{
                        position: 'absolute',
                        right: '12px',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        background: 'none',
                        border: 'none',
                        color: 'rgba(255, 255, 255, 0.4)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        padding: '4px'
                      }}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>
                <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '14px' }}>
                  Sign In to Suite
                </button>
              </form>
            ) : (
              <form onSubmit={handleRegister}>
                <div className="input-group">
                  <label className="input-label">Full Name</label>
                  <input 
                    type="text" 
                    required 
                    className="input-field" 
                    placeholder="John Doe"
                    value={regName}
                    onChange={(e) => setRegName(e.target.value)}
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Email Address</label>
                  <input 
                    type="email" 
                    required 
                    className="input-field" 
                    placeholder="john@broker.com"
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Password</label>
                  <div style={{ position: 'relative' }}>
                    <input 
                      type={showPassword ? "text" : "password"} 
                      required 
                      className="input-field" 
                      placeholder="Minimum 6 characters"
                      style={{ paddingRight: '40px' }}
                      value={regPassword}
                      onChange={(e) => setRegPassword(e.target.value)}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      style={{
                        position: 'absolute',
                        right: '12px',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        background: 'none',
                        border: 'none',
                        color: 'rgba(255, 255, 255, 0.4)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        padding: '4px'
                      }}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>
                <div className="input-group">
                  <label className="input-label">Account Type</label>
                  <select 
                    className="input-field select-field"
                    value={regAccountType}
                    onChange={(e) => setRegAccountType(e.target.value)}
                  >
                    <option value="broker">Broker Organization</option>
                    <option value="carrier">Carrier Organization</option>
                    <option value="shipper">Shipper (Individual or Business)</option>
                  </select>
                </div>

                {regAccountType !== 'shipper' && (
                  <div className="input-group" style={{ marginBottom: '28px' }}>
                    <label className="input-label">Organization Name</label>
                    <input 
                      type="text" 
                      required 
                      className="input-field" 
                      placeholder="e.g. Apex Logistics"
                      value={regOrgName}
                      onChange={(e) => setRegOrgName(e.target.value)}
                    />
                  </div>
                )}

                <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '14px' }}>
                  Register and Initialize
                </button>
              </form>
            )}

            <div style={{ textAlign: 'center', marginTop: '24px' }}>
              <button 
                type="button" 
                style={{ 
                  background: 'none', 
                  border: 'none', 
                  color: 'hsl(var(--primary))', 
                  cursor: 'pointer',
                  fontWeight: 600,
                  fontSize: '14px'
                }}
                onClick={() => {
                  setIsLogin(!isLogin);
                  setAuthError(null);
                }}
              >
                {isLogin ? "Don't have an account? Sign Up" : "Already registered? Sign In"}
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* Authenticated Dashboard Shell */
        <div className="dashboard-container">
          {/* Sidebar */}
          <div className="sidebar">
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '32px' }}>
              <div style={{ 
                padding: '8px', 
                borderRadius: '8px', 
                background: 'rgba(124, 58, 237, 0.15)',
                color: 'hsl(var(--primary))',
                border: '1px solid rgba(124, 58, 237, 0.25)'
              }}>
                <Truck size={24} />
              </div>
              <div>
                <h3 style={{ fontSize: '18px', color: '#fff', lineHeight: 1.2 }}>LoadFlow</h3>
                <span style={{ fontSize: '12px', color: 'hsl(var(--text-secondary))', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em' }}>
                  {currentUser?.account_type} {currentUser?.org && `| ${currentUser.org.name}`}
                </span>
              </div>
            </div>

            <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1 }}>
              <button 
                className={`btn ${currentTab === 'loads' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ justifyContent: 'flex-start', padding: '12px 16px' }}
                onClick={() => setCurrentTab('loads')}
              >
                <FileText size={18} />
                <span>Loads Board</span>
              </button>

              {currentUser?.account_type === 'carrier' && (
                <button 
                  className={`btn ${currentTab === 'compliance' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ justifyContent: 'flex-start', padding: '12px 16px' }}
                  onClick={() => setCurrentTab('compliance')}
                >
                  <Shield size={18} />
                  <span>Compliance Profile</span>
                </button>
              )}

              {currentUser?.permissions.includes('staff.manage') && (
                <>
                  <button 
                    className={`btn ${currentTab === 'staff' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ justifyContent: 'flex-start', padding: '12px 16px' }}
                    onClick={() => setCurrentTab('staff')}
                  >
                    <Users size={18} />
                    <span>Staff Directory</span>
                  </button>
                  <button 
                    className={`btn ${currentTab === 'roles' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ justifyContent: 'flex-start', padding: '12px 16px' }}
                    onClick={() => setCurrentTab('roles')}
                  >
                    <ShieldAlert size={18} />
                    <span>Role Catalog</span>
                  </button>
                </>
              )}

              {(currentUser?.account_type === 'broker' || currentUser?.account_type === 'carrier') && (
                <button 
                  className={`btn ${currentTab === 'logs' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ justifyContent: 'flex-start', padding: '12px 16px' }}
                  onClick={() => setCurrentTab('logs')}
                >
                  <Activity size={18} />
                  <span>Audit Trail</span>
                </button>
              )}
            </nav>

            <div style={{ 
              paddingTop: '24px', 
              borderTop: '1px solid hsl(var(--border-color))',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  background: 'rgba(255,255,255,0.05)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'hsl(var(--text-secondary))',
                  border: '1px solid hsl(var(--border-color))'
                }}>
                  <User size={18} />
                </div>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <p style={{ fontSize: '14px', color: '#fff', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {currentUser?.name}
                  </p>
                  <p style={{ fontSize: '11px', color: 'hsl(var(--text-muted))', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {currentUser?.email}
                  </p>
                </div>
              </div>
              <button 
                className="btn btn-secondary" 
                style={{ width: '100%', gap: '8px' }}
                onClick={handleLogout}
              >
                <LogOut size={16} />
                <span>Sign Out</span>
              </button>
            </div>
          </div>

          {/* Main Workspace */}
          <div className="main-content">
            {currentTab === 'loads' && (
              <div className="animate-fade-in">
                <div className="view-header">
                  <div>
                    <h1 style={{ fontSize: '32px', color: '#fff', marginBottom: '6px' }}>Loads Board</h1>
                    <p style={{ color: 'hsl(var(--text-secondary))' }}>Manage, check compliance, and track transport logistics</p>
                  </div>
                  {currentUser?.permissions.includes('load.create') && (
                    <button 
                      className="btn btn-primary"
                      onClick={() => {
                        loadShippers();
                        setShowCreateLoad(true);
                      }}
                    >
                      <Plus size={18} />
                      <span>Post a New Load</span>
                    </button>
                  )}
                </div>

                {/* Filter and Board Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: selectedLoad ? '1.2fr 1fr' : '1fr', gap: '32px' }}>
                  {/* Load Cards List */}
                  <div>
                    {loads.length === 0 ? (
                      <div className="card" style={{ textAlign: 'center', padding: '48px', borderStyle: 'dashed' }}>
                        <BookOpen size={40} style={{ color: 'hsl(var(--text-muted))', marginBottom: '16px' }} />
                        <h3 style={{ color: '#fff', marginBottom: '8px' }}>No Loads Registered</h3>
                        <p style={{ color: 'hsl(var(--text-secondary))' }}>Loads posted by shippers or brokers will show up here.</p>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        {loads.map(load => {
                          const rateConf = ratesMap[load.id]?.[0];
                          return (
                            <div 
                              key={load.id} 
                              className="card"
                              style={{ 
                                cursor: 'pointer',
                                borderColor: selectedLoad?.id === load.id ? 'hsl(var(--primary))' : 'hsl(var(--border-color))'
                              }}
                              onClick={() => {
                                setSelectedLoad(load);
                                if (load.carrier_id) {
                                  loadCarrierCompliance(load.carrier_id);
                                }
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                                <h3 style={{ fontSize: '18px', color: '#fff' }}>{load.title}</h3>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  {load.compliance_flag && (
                                    <span className="badge badge-danger" style={{ gap: '4px' }}>
                                      <AlertTriangle size={12} />
                                      <span>COMPLIANCE HOLD</span>
                                    </span>
                                  )}
                                  <span className={`badge ${getStatusBadgeClass(load.status)}`}>
                                    {load.status}
                                  </span>
                                </div>
                              </div>

                              <div style={{ display: 'flex', gap: '24px', color: 'hsl(var(--text-secondary))', fontSize: '14px', marginBottom: '16px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                  <MapPin size={16} />
                                  <span>{load.origin} → {load.destination}</span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                  <Truck size={16} />
                                  <span>{load.equipment_required}</span>
                                </div>
                              </div>

                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid rgba(255,255,255,0.03)', paddingTop: '16px' }}>
                                <span style={{ fontSize: '13px', color: 'hsl(var(--text-muted))' }}>
                                  Ref: #{load.id} | Cargo: {load.commodity_type}
                                </span>
                                {rateConf && (
                                  <span style={{ fontWeight: 700, color: 'hsl(var(--primary))' }}>
                                    ${rateConf.rate + rateConf.accessorials}
                                  </span>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* Detail Panel */}
                  {selectedLoad && (
                    <div className="glass-panel" style={{ padding: '32px', position: 'sticky', top: '40px', height: 'fit-content' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
                        <div>
                          <span style={{ fontSize: '12px', color: 'hsl(var(--primary))', fontWeight: 800, textTransform: 'uppercase' }}>Load Details</span>
                          <h2 style={{ fontSize: '24px', color: '#fff', marginTop: '4px' }}>{selectedLoad.title}</h2>
                        </div>
                        <button 
                          className="btn btn-secondary" 
                          style={{ padding: '4px 12px' }}
                          onClick={() => setSelectedLoad(null)}
                        >
                          Close
                        </button>
                      </div>

                      {/* Info grid */}
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
                        <div>
                          <p style={{ color: 'hsl(var(--text-muted))', fontSize: '12px' }}>Origin</p>
                          <p style={{ color: '#fff', fontWeight: 600 }}>{selectedLoad.origin}</p>
                        </div>
                        <div>
                          <p style={{ color: 'hsl(var(--text-muted))', fontSize: '12px' }}>Destination</p>
                          <p style={{ color: '#fff', fontWeight: 600 }}>{selectedLoad.destination}</p>
                        </div>
                        <div>
                          <p style={{ color: 'hsl(var(--text-muted))', fontSize: '12px' }}>Equipment Required</p>
                          <p style={{ color: '#fff', fontWeight: 600 }}>{selectedLoad.equipment_required}</p>
                        </div>
                        <div>
                          <p style={{ color: 'hsl(var(--text-muted))', fontSize: '12px' }}>Commodity Type</p>
                          <p style={{ color: '#fff', fontWeight: 600 }}>{selectedLoad.commodity_type}</p>
                        </div>
                      </div>

                      {/* Carrier Compliance info if carrier is assigned */}
                      {selectedLoad.carrier_id && complianceMap[selectedLoad.carrier_id] && (
                        <div style={{ background: 'rgba(255,255,255,0.01)', padding: '18px', borderRadius: '8px', border: '1px solid hsl(var(--border-color))', marginBottom: '24px' }}>
                          <h4 style={{ fontSize: '14px', marginBottom: '16px', color: '#fff', fontWeight: 600 }}>Assigned Carrier Compliance</h4>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', fontSize: '13px' }}>
                            <div>
                              <p style={{ color: 'hsl(var(--text-secondary))', marginBottom: '6px', fontSize: '12px' }}>FMCSA Authority</p>
                              <span className={`badge ${complianceMap[selectedLoad.carrier_id].authority_status === 'Active' ? 'badge-success' : 'badge-danger'}`}>
                                {complianceMap[selectedLoad.carrier_id].authority_status}
                              </span>
                            </div>
                            <div>
                              <p style={{ color: 'hsl(var(--text-secondary))', marginBottom: '6px', fontSize: '12px' }}>Insurance Expiry</p>
                              {(() => {
                                const expiry = complianceMap[selectedLoad.carrier_id].insurance_expiry;
                                const isExpired = !expiry || new Date(expiry) < new Date();
                                return (
                                  <span className={`badge ${isExpired ? 'badge-danger' : 'badge-success'}`}>
                                    {expiry || 'Lapsed/Missing'}
                                  </span>
                                );
                              })()}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* State machine progress */}
                      <div style={{ background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '8px', border: '1px solid hsl(var(--border-color))', marginBottom: '24px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                          <span style={{ fontSize: '13px', fontWeight: 700 }}>Status Progress</span>
                          <span className={`badge ${getStatusBadgeClass(selectedLoad.status)}`}>{selectedLoad.status}</span>
                        </div>
                        
                        {/* Map-like visual track - Premium Vertical Stepper */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '16px', marginBottom: '24px', paddingLeft: '8px' }}>
                          {["Posted", "Carrier Assigned", "Rate Confirmed", "Dispatched", "In Transit", "Delivered", "POD Verified", "Closed"].map((st, i) => {
                            const activeIdx = getStatusFlowIndex(selectedLoad.status);
                            const isCurrent = i === activeIdx;
                            const isPast = i < activeIdx;
                            return (
                              <div key={st} style={{ display: 'flex', alignItems: 'center', gap: '16px', position: 'relative' }}>
                                {i < 7 && (
                                  <div style={{
                                    position: 'absolute',
                                    left: '7px',
                                    top: '18px',
                                    bottom: '-22px',
                                    width: '2px',
                                    background: isPast ? 'hsl(var(--primary))' : 'rgba(255,255,255,0.06)'
                                  }} />
                                )}
                                <div style={{ 
                                  width: '16px', 
                                  height: '16px', 
                                  borderRadius: '50%', 
                                  border: `2px solid ${isCurrent || isPast ? 'hsl(var(--primary))' : 'rgba(255,255,255,0.15)'}`,
                                  background: isCurrent ? 'hsl(var(--primary))' : 'transparent',
                                  boxShadow: isCurrent ? '0 0 10px hsl(var(--primary))' : 'none',
                                  zIndex: 1,
                                  transition: 'all var(--transition-normal)'
                                }} />
                                <span style={{ 
                                  fontSize: '13px', 
                                  fontWeight: isCurrent ? 700 : 500,
                                  color: isCurrent ? '#fff' : isPast ? 'hsl(var(--text-secondary))' : 'hsl(var(--text-muted))'
                                }}>
                                  {st}
                                </span>
                              </div>
                            );
                          })}
                        </div>

                        {/* Interactive Status Transition advances */}
                        {currentUser?.permissions.includes('load.update_status') && (
                          <div style={{ display: 'flex', gap: '8px' }}>
                            {selectedLoad.status === 'Rate Confirmed' && (
                              <button className="btn btn-primary" style={{ flex: 1 }} onClick={() => handleAdvanceStatus(selectedLoad.id, 'Dispatched')}>
                                Mark Dispatched
                              </button>
                            )}
                            {selectedLoad.status === 'Dispatched' && (
                              <button className="btn btn-primary" style={{ flex: 1 }} onClick={() => handleAdvanceStatus(selectedLoad.id, 'In Transit')}>
                                Mark In Transit
                              </button>
                            )}
                            {selectedLoad.status === 'In Transit' && (
                              <button className="btn btn-primary" style={{ flex: 1 }} onClick={() => handleAdvanceStatus(selectedLoad.id, 'Delivered')}>
                                Mark Delivered
                              </button>
                            )}
                            {selectedLoad.status === 'Delivered' && selectedLoad.pod_url && (
                              <button className="btn btn-primary" style={{ flex: 1 }} onClick={() => handleAdvanceStatus(selectedLoad.id, 'POD Verified')}>
                                Verify POD Document
                              </button>
                            )}
                            {selectedLoad.status === 'POD Verified' && (
                              <button className="btn btn-primary" style={{ flex: 1 }} onClick={() => handleAdvanceStatus(selectedLoad.id, 'Closed')}>
                                Close Shipment / Invoice
                              </button>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Compliance Banner & Override */}
                      {selectedLoad.compliance_flag && (
                        <div style={{ 
                          background: 'rgba(239, 68, 68, 0.1)', 
                          border: '1px solid rgba(239, 68, 68, 0.3)', 
                          padding: '16px', 
                          borderRadius: '8px', 
                          color: '#f87171',
                          marginBottom: '24px'
                        }}>
                          <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start', marginBottom: '8px' }}>
                            <AlertTriangle size={20} />
                            <div>
                              <p style={{ fontWeight: 700 }}>Compliance Lock Active</p>
                              <p style={{ fontSize: '13px', opacity: 0.9 }}>
                                Assigned carrier insurance has lapsed, authority status is inactive, or equipment requirements do not match.
                              </p>
                            </div>
                          </div>
                          {currentUser?.permissions.includes('load.override_compliance_flag') && (
                            <button 
                              className="btn btn-danger" 
                              style={{ width: '100%', fontSize: '13px', padding: '8px 16px', marginTop: '8px' }}
                              onClick={() => {
                                // If they advance to Rate Confirmed, state machine automatically processes override
                                handleAdvanceStatus(selectedLoad.id, 'Rate Confirmed');
                              }}
                            >
                              Override Lock & Confirm Rate
                            </button>
                          )}
                        </div>
                      )}

                      {/* Carriers List Assignment Wizard */}
                      {selectedLoad.status === 'Posted' && currentUser?.permissions.includes('load.assign_carrier') && (
                        <div style={{ background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '8px', border: '1px solid hsl(var(--border-color))', marginBottom: '24px' }}>
                          <h4 style={{ fontSize: '14px', marginBottom: '12px' }}>Assign Carrier Organization</h4>
                          <div style={{ display: 'flex', gap: '10px' }}>
                            <select 
                              className="input-field select-field" 
                              style={{ flex: 1 }}
                              value={assignCarrierId || ''}
                              onChange={(e) => setAssignCarrierId(e.target.value !== '' ? Number(e.target.value) : null)}
                            >
                              <option value="">Select Carrier...</option>
                              {carriers.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                            </select>
                            <button 
                              className="btn btn-primary"
                              disabled={assignCarrierId === null}
                              onClick={() => handleAssignCarrier(selectedLoad.id)}
                            >
                              Assign
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Rates Agreement Section */}
                      {(selectedLoad.status === 'Posted' || selectedLoad.status === 'Carrier Assigned') && currentUser?.permissions.includes('rate.confirm') && (
                        <div style={{ background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '8px', border: '1px solid hsl(var(--border-color))', marginBottom: '24px' }}>
                          <h4 style={{ fontSize: '14px', marginBottom: '12px' }}>Propose Rate Confirmation</h4>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                            <div>
                              <label className="input-label" style={{ fontSize: '11px' }}>Line Haul Rate ($)</label>
                              <input type="number" className="input-field" value={rateAmount} onChange={(e) => setRateAmount(Number(e.target.value))} />
                            </div>
                            <div>
                              <label className="input-label" style={{ fontSize: '11px' }}>Accessorials ($)</label>
                              <input type="number" className="input-field" value={accessorialsAmount} onChange={(e) => setAccessorialsAmount(Number(e.target.value))} />
                            </div>
                          </div>
                          <button className="btn btn-primary" style={{ width: '100%' }} onClick={() => handleProposeRate(selectedLoad.id)}>
                            Post Rate Agreement
                          </button>
                        </div>
                      )}

                      {/* Display Rate Proposals to confirm */}
                      {ratesMap[selectedLoad.id]?.map((rateProposal, idx) => (
                        <div key={idx} style={{ 
                          background: 'rgba(124, 58, 237, 0.05)', 
                          border: '1px dashed rgba(124, 58, 237, 0.3)', 
                          padding: '16px', 
                          borderRadius: '8px',
                          marginBottom: '24px'
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                            <span style={{ fontSize: '13px', fontWeight: 700 }}>Rate Confirmation v{rateProposal.version}</span>
                            <span style={{ fontSize: '12px', color: 'hsl(var(--text-secondary))' }}>
                              {rateProposal.confirmed_by ? 'Signed' : 'Unsigned'}
                            </span>
                          </div>
                          <p style={{ color: '#fff', fontSize: '18px', fontWeight: 800 }}>
                            ${rateProposal.rate} + ${rateProposal.accessorials} accessorials
                          </p>
                          {!rateProposal.confirmed_by && currentUser?.permissions.includes('rate.confirm') && (
                            <button 
                              className="btn btn-primary" 
                              style={{ width: '100%', marginTop: '12px', fontSize: '13px', padding: '8px 16px' }}
                              onClick={() => handleConfirmRate(selectedLoad.id, rateProposal.version)}
                            >
                              Sign & Approve Rate
                            </button>
                          )}
                        </div>
                      ))}

                      {/* Carrier Upload POD */}
                      {currentUser?.account_type === 'carrier' && (selectedLoad.status === 'In Transit' || selectedLoad.status === 'Delivered') && (
                        <div style={{ background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '8px', border: '1px solid hsl(var(--border-color))' }}>
                          <h4 style={{ fontSize: '14px', marginBottom: '12px' }}>Upload POD (Proof of Delivery)</h4>
                          <input 
                            type="text" 
                            className="input-field" 
                            placeholder="Enter POD URL or document metadata" 
                            value={podBase64} 
                            onChange={(e) => setPodBase64(e.target.value)} 
                            style={{ marginBottom: '12px' }}
                          />
                          <button 
                            className="btn btn-primary" 
                            style={{ width: '100%' }}
                            disabled={!podBase64}
                            onClick={() => handleUploadPod(selectedLoad.id)}
                          >
                            <Upload size={16} />
                            <span>Upload Document</span>
                          </button>
                        </div>
                      )}

                      {/* Display POD if uploaded */}
                      {selectedLoad.pod_url && (
                        <div style={{ marginTop: '24px', borderTop: '1px solid hsl(var(--border-color))', paddingTop: '16px' }}>
                          <p style={{ color: 'hsl(var(--text-muted))', fontSize: '12px' }}>Proof of Delivery (POD)</p>
                          <div style={{ 
                            background: 'rgba(0,0,0,0.2)', 
                            padding: '12px', 
                            borderRadius: '6px', 
                            color: 'hsl(var(--success))',
                            fontSize: '13px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            marginTop: '8px'
                          }}>
                            <CheckCircle size={16} />
                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{selectedLoad.pod_url}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            {currentTab === 'compliance' && (
              <div className="animate-fade-in" style={{ maxWidth: '640px' }}>
                <div className="view-header">
                  <div>
                    <h1 style={{ fontSize: '32px', color: '#fff', marginBottom: '6px' }}>Compliance Credentials</h1>
                    <p style={{ color: 'hsl(var(--text-secondary))' }}>Configure carrier insurance, authority credentials, and equipment lists</p>
                  </div>
                </div>

                <div className="glass-panel" style={{ padding: '36px' }}>
                  <form onSubmit={handleUpdateCompliance}>
                    <div className="input-group">
                      <label className="input-label">Insurance Expiry Date</label>
                      <input 
                        type="date" 
                        required 
                        className="input-field"
                        value={compInsuranceExpiry}
                        onChange={(e) => setCompInsuranceExpiry(e.target.value)}
                      />
                    </div>

                    <div className="input-group">
                      <label className="input-label">FMCSA Authority Status</label>
                      <select 
                        className="input-field select-field"
                        value={compAuthority}
                        onChange={(e) => setCompAuthority(e.target.value)}
                      >
                        <option value="Active">Active / Approved</option>
                        <option value="Inactive">Inactive / Suspended</option>
                      </select>
                    </div>

                    <div className="input-group">
                      <label className="input-label">Approved Equipment</label>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '8px' }}>
                        {['Reefer', 'Flatbed', 'Dry Van', 'Power Only'].map(eq => (
                          <label key={eq} style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                            <input 
                              type="checkbox" 
                              checked={compEquipment.includes(eq)} 
                              onChange={(e) => {
                                if (e.target.checked) setCompEquipment([...compEquipment, eq]);
                                else setCompEquipment(compEquipment.filter(x => x !== eq));
                              }}
                            />
                            <span>{eq}</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    <div className="input-group" style={{ marginBottom: '32px' }}>
                      <label className="input-label">Approved Cargo Commodities</label>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '8px' }}>
                        {['Food', 'General', 'Hazmat', 'Electronics'].map(com => (
                          <label key={com} style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                            <input 
                              type="checkbox" 
                              checked={compCommodities.includes(com)} 
                              onChange={(e) => {
                                if (e.target.checked) setCompCommodities([...compCommodities, com]);
                                else setCompCommodities(compCommodities.filter(x => x !== com));
                              }}
                            />
                            <span>{com}</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>
                      Save Compliance Profile
                    </button>
                  </form>
                </div>
              </div>
            )}

            {currentTab === 'staff' && (
              <div className="animate-fade-in">
                <div className="view-header">
                  <div>
                    <h1 style={{ fontSize: '32px', color: '#fff', marginBottom: '6px' }}>Staff Directory</h1>
                    <p style={{ color: 'hsl(var(--text-secondary))' }}>Manage users and scope-level authorizations inside your organization</p>
                  </div>
                  <button className="btn btn-primary" onClick={() => setShowCreateStaff(true)}>
                    <Plus size={18} />
                    <span>Invite Team Member</span>
                  </button>
                </div>

                <div className="glass-panel" style={{ padding: '24px', overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid hsl(var(--border-color))' }}>
                        <th style={{ padding: '16px', color: 'hsl(var(--text-muted))', fontSize: '13px' }}>Name</th>
                        <th style={{ padding: '16px', color: 'hsl(var(--text-muted))', fontSize: '13px' }}>Email</th>
                        <th style={{ padding: '16px', color: 'hsl(var(--text-muted))', fontSize: '13px' }}>Role</th>
                        <th style={{ padding: '16px', color: 'hsl(var(--text-muted))', fontSize: '13px' }}>Permissions Assigned</th>
                      </tr>
                    </thead>
                    <tbody>
                      {staff.map(s => (
                        <tr key={s.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                          <td style={{ padding: '16px', fontWeight: 600, color: '#fff' }}>{s.name}</td>
                          <td style={{ padding: '16px', color: 'hsl(var(--text-secondary))' }}>{s.email}</td>
                          <td style={{ padding: '16px' }}>
                            <span className="badge" style={{
                              background: 'rgba(255,255,255,0.04)',
                              border: '1px solid hsl(var(--border-color))',
                              color: '#fff',
                              whiteSpace: 'nowrap'
                            }}>
                              {s.role_id ? 'Scoped Role' : 'Org Admin'}
                            </span>
                          </td>
                          <td style={{ padding: '16px' }}>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                              {s.permissions.map(p => (
                                <span key={p} className="badge" style={{
                                  background: 'rgba(99, 102, 241, 0.06)',
                                  border: '1px solid rgba(99, 102, 241, 0.15)',
                                  color: 'hsl(var(--primary))',
                                  whiteSpace: 'nowrap'
                                }}>
                                  {p}
                                </span>
                              ))}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {currentTab === 'roles' && (
              <div className="animate-fade-in" style={{ maxWidth: '800px' }}>
                <div className="view-header">
                  <div>
                    <h1 style={{ fontSize: '32px', color: '#fff', marginBottom: '6px' }}>Role Catalog</h1>
                    <p style={{ color: 'hsl(var(--text-secondary))' }}>Define custom permission templates for your organization staff</p>
                  </div>
                  <button className="btn btn-primary" onClick={() => setShowCreateRole(true)}>
                    <Plus size={18} />
                    <span>Create Custom Role</span>
                  </button>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px' }}>
                  {roles.map(r => (
                    <div key={r.id} className="card">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                        <Shield size={24} style={{ color: 'hsl(var(--primary))' }} />
                        <h3 style={{ fontSize: '18px', color: '#fff' }}>{r.role_name}</h3>
                      </div>
                      <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '13px' }}>
                        Template role created for specialized authorization flow mapping.
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {currentTab === 'logs' && (
              <div className="animate-fade-in" style={{ maxWidth: '900px' }}>
                <div className="view-header">
                  <div>
                    <h1 style={{ fontSize: '32px', color: '#fff', marginBottom: '6px' }}>Audit Trail History</h1>
                    <p style={{ color: 'hsl(var(--text-secondary))' }}>Immutable record of all operational modifications, signoffs, and security logs</p>
                  </div>
                </div>

                <div className="glass-panel" style={{ padding: '24px' }}>
                  {auditLogs.length === 0 ? (
                    <p style={{ textAlign: 'center', padding: '32px', color: 'hsl(var(--text-muted))' }}>No audit trails recorded yet.</p>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      {auditLogs.map(log => (
                        <div 
                          key={log.id} 
                          style={{ 
                            background: 'rgba(255,255,255,0.01)', 
                            border: '1px solid hsl(var(--border-color))',
                            padding: '16px',
                            borderRadius: '8px',
                            display: 'flex',
                            gap: '16px',
                            alignItems: 'flex-start'
                          }}
                        >
                          <div style={{
                            padding: '8px',
                            borderRadius: '6px',
                            background: log.action.includes('DENIED') || log.action.includes('BLOCK') ? 'rgba(239, 68, 68, 0.1)' : 'rgba(255,255,255,0.03)',
                            color: log.action.includes('DENIED') || log.action.includes('BLOCK') ? '#f87171' : 'hsl(var(--primary))'
                          }}>
                            <Clock size={18} />
                          </div>
                          <div style={{ flex: 1 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                              <span style={{ fontWeight: 700, color: '#fff' }}>{log.action}</span>
                              <span style={{ fontSize: '11px', color: 'hsl(var(--text-muted))' }}>
                                {new Date(log.created_at).toLocaleString()}
                              </span>
                            </div>
                            <p style={{ fontSize: '13px', color: 'hsl(var(--text-secondary))', marginBottom: '4px' }}>
                              {log.details}
                            </p>
                            <span style={{ fontSize: '11px', color: 'hsl(var(--text-muted))' }}>
                              Triggered by: {log.user_email || 'System'}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* CREATE LOAD MODAL */}
      {showCreateLoad && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.8)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 999
        }}>
          <div className="glass-panel" style={{ padding: '36px', width: '100%', maxWidth: '520px' }}>
            <h2 style={{ color: '#fff', marginBottom: '24px' }}>Post New Load</h2>
            <form onSubmit={handleCreateLoad}>
              <div className="input-group">
                <label className="input-label">Load Title</label>
                <input type="text" required className="input-field" placeholder="e.g. Frozen Fish Delivery" value={newLoadTitle} onChange={(e) => setNewLoadTitle(e.target.value)} />
              </div>
              <div className="input-group">
                <label className="input-label">Origin Location</label>
                <input type="text" required className="input-field" placeholder="City, State" value={newLoadOrigin} onChange={(e) => setNewLoadOrigin(e.target.value)} />
              </div>
              <div className="input-group">
                <label className="input-label">Destination Location</label>
                <input type="text" required className="input-field" placeholder="City, State" value={newLoadDest} onChange={(e) => setNewLoadDest(e.target.value)} />
              </div>
              <div className="input-group">
                <label className="input-label">Equipment Required</label>
                <select className="input-field select-field" value={newLoadEq} onChange={(e) => setNewLoadEq(e.target.value)}>
                  <option value="Reefer">Reefer</option>
                  <option value="Flatbed">Flatbed</option>
                  <option value="Dry Van">Dry Van</option>
                  <option value="Power Only">Power Only</option>
                </select>
              </div>
              <div className="input-group">
                <label className="input-label">Commodity Type</label>
                <select className="input-field select-field" value={newLoadComm} onChange={(e) => setNewLoadComm(e.target.value)}>
                  <option value="Food">Food</option>
                  <option value="General">General</option>
                  <option value="Hazmat">Hazmat</option>
                  <option value="Electronics">Electronics</option>
                </select>
              </div>
              <div className="input-group" style={{ marginBottom: '32px' }}>
                <label className="input-label">Client Shipper Account</label>
                <select required className="input-field select-field" value={newLoadShipperId || ''} onChange={(e) => setNewLoadShipperId(e.target.value !== '' ? Number(e.target.value) : null)}>
                  <option value="">Select Shipper...</option>
                  {shippers.map(s => <option key={s.id} value={s.id}>{s.name} ({s.email})</option>)}
                </select>
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>Create Load</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateLoad(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CREATE STAFF MODAL */}
      {showCreateStaff && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.8)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 999
        }}>
          <div className="glass-panel" style={{ padding: '36px', width: '100%', maxWidth: '480px' }}>
            <h2 style={{ color: '#fff', marginBottom: '24px' }}>Invite Staff Member</h2>
            <form onSubmit={handleCreateStaff}>
              <div className="input-group">
                <label className="input-label">Staff Name</label>
                <input type="text" required className="input-field" placeholder="Full Name" value={newStaffName} onChange={(e) => setNewStaffName(e.target.value)} />
              </div>
              <div className="input-group">
                <label className="input-label">Staff Email Address</label>
                <input type="email" required className="input-field" placeholder="email@organization.com" value={newStaffEmail} onChange={(e) => setNewStaffEmail(e.target.value)} />
              </div>
              <div className="input-group">
                <label className="input-label">Temporary Password</label>
                <input type="password" required className="input-field" placeholder="••••••••" value={newStaffPassword} onChange={(e) => setNewStaffPassword(e.target.value)} />
              </div>
              <div className="input-group" style={{ marginBottom: '32px' }}>
                <label className="input-label">Assigned Custom Role</label>
                <select required className="input-field select-field" value={newStaffRoleId || ''} onChange={(e) => setNewStaffRoleId(e.target.value !== '' ? Number(e.target.value) : null)}>
                  <option value="">Select Role...</option>
                  {roles.map(r => <option key={r.id} value={r.id}>{r.role_name}</option>)}
                </select>
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>Invite User</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateStaff(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CREATE ROLE MODAL */}
      {showCreateRole && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.8)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 999
        }}>
          <div className="glass-panel" style={{ padding: '36px', width: '100%', maxWidth: '520px' }}>
            <h2 style={{ color: '#fff', marginBottom: '24px' }}>Create Custom Role</h2>
            <form onSubmit={handleCreateRole}>
              <div className="input-group" style={{ marginBottom: '24px' }}>
                <label className="input-label">Role Title</label>
                <input type="text" required className="input-field" placeholder="e.g. Senior Dispatcher" value={newRoleName} onChange={(e) => setNewRoleName(e.target.value)} />
              </div>
              
              <div className="input-group" style={{ marginBottom: '32px' }}>
                <label className="input-label">Select Granted Permissions</label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '200px', overflowY: 'auto', background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '6px' }}>
                  {permissionsCatalog.map(p => (
                    <label key={p.id} style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
                      <input 
                        type="checkbox" 
                        checked={newRolePerms.includes(p.id)} 
                        onChange={() => handleTogglePerm(p.id)}
                      />
                      <span style={{ fontSize: '14px', color: '#fff' }}>{p.permission_name}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>Save Role</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateRole(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
