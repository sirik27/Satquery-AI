/**
 * Login Page — Email/password login + signup with Firebase Auth.
 * Features a premium gradient background with glassmorphism card.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Satellite, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const [isSignup, setIsSignup] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const { login, signup } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isSignup) {
        await signup(email, password, name);
      } else {
        await login(email, password);
      }
      navigate('/', { replace: true });
    } catch (err) {
      console.error('Auth error:', err);
      const code = err.code || '';
      if (code.includes('user-not-found') || code.includes('wrong-password') || code.includes('invalid-credential')) {
        setError('Invalid email or password. Please try again.');
      } else if (code.includes('email-already-in-use')) {
        setError('An account with this email already exists.');
      } else if (code.includes('weak-password')) {
        setError('Password should be at least 6 characters.');
      } else if (code.includes('invalid-email')) {
        setError('Please enter a valid email address.');
      } else {
        setError(err.message || 'Authentication failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page" id="login-page">
      <div className="login-card">
        <div className="logo-section">
          <div className="logo-badge">
            <Satellite size={26} />
          </div>
          <h1>DrishtiAI</h1>
          <p>Satellite Intelligence Platform</p>
        </div>

        <form onSubmit={handleSubmit}>
          {isSignup && (
            <div className="form-group">
              <label htmlFor="input-name">Full Name</label>
              <input
                id="input-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter your name"
                autoComplete="name"
              />
            </div>
          )}

          <div className="form-group">
            <label htmlFor="input-email">Email Address</label>
            <input
              id="input-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label htmlFor="input-password">Password</label>
            <div style={{ position: 'relative' }}>
              <input
                id="input-password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                autoComplete={isSignup ? 'new-password' : 'current-password'}
                style={{ paddingRight: 40 }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: 10,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: '#94a3b8',
                  padding: 4,
                }}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {error && <div className="form-error">{error}</div>}

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            style={{ width: '100%', justifyContent: 'center', marginTop: 8, padding: '12px 0' }}
            id="btn-submit-auth"
          >
            {loading ? (
              <div className="spinner" />
            ) : isSignup ? (
              'Create Account'
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        <div className="form-toggle">
          <button onClick={() => { setIsSignup(!isSignup); setError(''); }}>
            {isSignup ? 'Already have an account? Sign in' : "Don't have an account? Sign up"}
          </button>
        </div>
      </div>
    </div>
  );
}
