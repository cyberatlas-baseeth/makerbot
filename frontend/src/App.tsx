import { useState } from 'react';
import LoginPage from './components/LoginPage';
import Dashboard from './components/Dashboard';

interface AuthState {
  token: string;
  address: string;
}

function App() {
  const [auth, setAuth] = useState<AuthState | null>(null);

  const handleAuthenticated = (token: string, address: string) => {
    setAuth({ token, address });
  };

  if (!auth) {
    return <LoginPage onAuthenticated={handleAuthenticated} />;
  }

  return <Dashboard address={auth.address} />;
}

export default App;
