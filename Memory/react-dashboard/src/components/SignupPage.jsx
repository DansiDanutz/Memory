import React, { useState } from 'react';
import { API_BASE_URL } from '../config';

const SignupPage = ({ onSignupSuccess, onSwitchToLogin }) => {
  const [formData, setFormData] = useState({
    name: '',
    phone_number: '',
    password: '',
    confirmPassword: ''
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

    // Validation
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters long');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          name: formData.name,
          phone_number: formData.phone_number,
          password: formData.password
        })
      });

      const data = await response.json();

      if (data.success) {
        onSignupSuccess(data.user);
      } else {
        setError(data.message || 'Signup failed');
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
          <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
            <div style={{ 
              width: '60px', 
              height: '60px', 
              background: 'linear-gradient(135deg, #25D366 0%, #128C7E 100%)',
              borderRadius: '50%',
              margin: '0 auto 1rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.5rem',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)'
            }}>
              🧠
            </div>
            <h1 className="section-title" style={{ fontSize: '1.8rem' }}>Your Second Brain</h1>
            <p className="section-subtitle" style={{ fontSize: '0.9rem' }}>for Life's Moments</p>
          </div>

          {/* Features Preview */}
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(2, 1fr)', 
            gap: '0.8rem', 
            marginBottom: '1.5rem' 
          }}>
            <div className="feature-card" style={{ padding: '1rem' }}>
              <div className="feature-icon" style={{ fontSize: '1.5rem' }}>🤖</div>
              <div className="feature-title" style={{ fontSize: '0.9rem' }}>AI Memory</div>
              <div className="feature-description" style={{ fontSize: '0.8rem' }}>Never forget</div>
            </div>
            <div className="feature-card" style={{ padding: '1rem' }}>
              <div className="feature-icon" style={{ fontSize: '1.5rem' }}>🔒</div>
              <div className="feature-title" style={{ fontSize: '0.9rem' }}>Secure Vault</div>
              <div className="feature-description" style={{ fontSize: '0.8rem' }}>Protected</div>
            </div>
            <div className="feature-card" style={{ padding: '1rem' }}>
              <div className="feature-icon" style={{ fontSize: '1.5rem' }}>💝</div>
              <div className="feature-title" style={{ fontSize: '0.9rem' }}>Feelings</div>
              <div className="feature-description" style={{ fontSize: '0.8rem' }}>AI detects</div>
            </div>
            <div className="feature-card" style={{ padding: '1rem' }}>
              <div className="feature-icon" style={{ fontSize: '1.5rem' }}>🌍</div>
              <div className="feature-title" style={{ fontSize: '0.9rem' }}>Community</div>
              <div className="feature-description" style={{ fontSize: '0.8rem' }}>Connected</div>
            </div>
          </div>

          {/* Stats */}
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(3, 1fr)', 
            gap: '0.8rem', 
            marginBottom: '1.5rem',
            textAlign: 'center'
          }}>
            <div>
              <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#FFB800' }}>50K+</div>
              <div style={{ fontSize: '0.7rem', color: 'rgba(255, 255, 255, 0.7)' }}>USERS</div>
            </div>
            <div>
              <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#FFB800' }}>2M+</div>
              <div style={{ fontSize: '0.7rem', color: 'rgba(255, 255, 255, 0.7)' }}>MEMORIES</div>
            </div>
            <div>
              <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#FFB800' }}>99.9%</div>
              <div style={{ fontSize: '0.7rem', color: 'rgba(255, 255, 255, 0.7)' }}>UPTIME</div>
            </div>
          </div>

          {/* Signup Form */}
          <div style={{ 
            background: 'rgba(255, 255, 255, 0.05)',
            borderRadius: '16px',
            padding: '1.2rem',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            flex: 1
          }}>
            <h2 className="section-title" style={{ fontSize: '1.3rem', marginBottom: '0.8rem' }}>Create Account</h2>
            <p className="section-subtitle" style={{ marginBottom: '1.2rem', fontSize: '0.8rem' }}>Join thousands who trust Memory Assistant</p>

            <form onSubmit={handleSubmit}>
              <div className="form-group" style={{ marginBottom: '1rem' }}>
                <label className="form-label" style={{ fontSize: '0.8rem' }}>Full Name</label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="Enter your full name"
                  className="form-input"
                  style={{ padding: '0.8rem', fontSize: '0.9rem' }}
                  required
                />
              </div>

              <div className="form-group" style={{ marginBottom: '1rem' }}>
                <label className="form-label" style={{ fontSize: '0.8rem' }}>Phone Number</label>
                <input
                  type="tel"
                  name="phone_number"
                  value={formData.phone_number}
                  onChange={handleChange}
                  placeholder="+1 (555) 123-4567"
                  className="form-input"
                  style={{ padding: '0.8rem', fontSize: '0.9rem' }}
                  required
                />
              </div>

              <div className="form-group" style={{ marginBottom: '1rem' }}>
                <label className="form-label" style={{ fontSize: '0.8rem' }}>Password</label>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="Create a secure password"
                  className="form-input"
                  style={{ padding: '0.8rem', fontSize: '0.9rem' }}
                  required
                />
              </div>

              <div className="form-group" style={{ marginBottom: '1rem' }}>
                <label className="form-label" style={{ fontSize: '0.8rem' }}>Confirm Password</label>
                <input
                  type="password"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="Confirm your password"
                  className="form-input"
                  style={{ padding: '0.8rem', fontSize: '0.9rem' }}
                  required
                />
              </div>

              {error && (
                <div className="error-message" style={{ padding: '0.8rem', fontSize: '0.8rem' }}>
                  {error}
                </div>
              )}

              <button 
                type="submit" 
                className="btn-primary"
                disabled={loading}
                style={{ padding: '0.8rem', fontSize: '0.9rem' }}
              >
                {loading && <span className="loading-spinner"></span>}
                Create Account
              </button>
            </form>

            <div style={{ textAlign: 'center', marginTop: '1rem' }}>
              <p style={{ color: 'rgba(255, 255, 255, 0.7)', fontSize: '0.8rem' }}>
                Already have an account?{' '}
                <button 
                  type="button"
                  onClick={onSwitchToLogin}
                  className="link"
                  style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.8rem' }}
                >
                  Sign In
                </button>
              </p>
            </div>
          </div>

          {/* Terms */}
          <div style={{ 
            textAlign: 'center', 
            marginTop: '1rem', 
            fontSize: '0.7rem', 
            color: 'rgba(255, 255, 255, 0.6)' 
          }}>
            By creating an account, you agree to our Terms of Service and Privacy Policy.
          </div>
        </div>
      </div>
    </div>
  );
};

export default SignupPage;

