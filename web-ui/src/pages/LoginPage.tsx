import { type FormEvent, useState } from 'react';
import { login } from '../api/client';

interface LoginPageProps {
  onLogin: () => void;
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    try {
      await login(password);
      onLogin();
    } catch {
      setError('Invalid password');
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="bg-bg-secondary border border-border-primary rounded-lg p-8 w-[340px]">
        <h1 className="text-2xl font-semibold text-accent mb-2">NoClaw</h1>
        <p className="text-text-muted text-sm mb-6">Enter password to access the control panel</p>
        {error && <p className="text-danger text-sm mb-3">{error}</p>}
        <form onSubmit={handleSubmit}>
          <label className="block text-xs text-text-muted mb-1.5">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoFocus
            className="w-full px-3 py-2 rounded-md border border-border-primary bg-bg-primary text-text-secondary text-sm mb-4 focus:outline-none focus:border-accent"
          />
          <button
            type="submit"
            className="w-full py-2.5 rounded-md bg-success hover:bg-success-hover text-white text-sm font-semibold cursor-pointer"
          >
            Sign In
          </button>
        </form>
      </div>
    </div>
  );
}
