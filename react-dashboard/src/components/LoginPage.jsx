import React, { useState } from 'react';
import { API_BASE_URL } from '../config';

const LoginPage = ({ onLoginSuccess, onSwitchToSignup }) => {
  const [formData, setFormData] = useState({
    phone_number: '',
    password: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(formData)
      });

      const data = await response.json();

      if (data.success) {
        onLoginSuccess(data.user, data.session_token);
      } else {
        setError(data.message || 'Login failed');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <div className="phone-mockup">
        <div className="phone-content">
          {/* App Header */}
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <div style={{ 
              width: '80px', 
              height: '80px', 
              background: 'linear-gradient(135deg, #25D366 0%, #128C7E 100%)',
              borderRadius: '50%',
              margin: '0 auto 1rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '2rem',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)'
            }}>
              🧠
            </div>
            <h1 className="section-title">Welcome Back</h1>
            <p className="section-subtitle">Sign in to access your AI-powered memories</p>
          </div>

          {/* Login Form */}
          <form onSubmit={handleSubmit} style={{ flex: 1 }}>
            <div className="form-group">
              <label className="form-label">Phone Number</label>
              <input
                type="tel"
                name="phone_number"
                value={formData.phone_number}
                onChange={handleChange}
                placeholder="+1 (555) 123-4567"
                className="form-input"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Enter your password"
                className="form-input"
                required
              />
            </div>

            {error && (
              <div className="error-message">
                {error}
              </div>
            )}

            <button 
              type="submit" 
              className="btn-primary"
              disabled={loading}
            >
              {loading && <span className="loading-spinner"></span>}
              Sign In
            </button>
          </form>

          {/* Footer Links */}
          <div style={{ textAlign: 'center', marginTop: '1.5rem' }}>
            <button 
              type="button"
              className="btn-secondary"
              style={{ marginBottom: '1rem', width: '100%' }}
            >
              Forgot your password?
            </button>
            
            <p style={{ color: 'rgba(255, 255, 255, 0.7)', fontSize: '0.9rem' }}>
              Don't have an account?{' '}
              <button 
                type="button"
                onClick={onSwitchToSignup}
                className="link"
                style={{ background: 'none', border: 'none', cursor: 'pointer' }}
              >
                Create Account
              </button>
            </p>
          </div>

          {/* Security Notice */}
          <div style={{ 
            textAlign: 'center', 
            marginTop: '2rem', 
            fontSize: '0.8rem', 
            color: 'rgba(255, 255, 255, 0.6)' 
          }}>
            Your conversations are encrypted and secure. We never share your personal data.
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;

