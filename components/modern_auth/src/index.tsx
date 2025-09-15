import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Streamlit, withStreamlitConnection } from 'streamlit-component-lib';
import LoginForm from './LoginForm';
import './styles.css';

interface AuthComponentProps {
  args: {
    loading?: boolean;
    error_message?: string;
    success_message?: string;
    theme?: 'light' | 'dark';
    language?: 'fr' | 'en';
  };
}

const ModernAuthComponent: React.FC<AuthComponentProps> = ({ args }) => {
  const [loading, setLoading] = useState(args?.loading || false);
  const [error, setError] = useState<string | null>(args?.error_message || null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    // Informer Streamlit que le composant est prêt
    Streamlit.setFrameHeight(600);
  }, []);

  // Réagir aux changements d'props depuis Python
  useEffect(() => {
    if (args) {
      setLoading(args.loading || false);
      setError(args.error_message || null);
      
      if (args.success_message) {
        setSuccess(true);
        setTimeout(() => setSuccess(false), 3000);
      }
    }
  }, [args]);

  const handleLogin = async (username: string, password: string) => {
    setLoading(true);
    setError(null);
    
    // Envoyer les données d'authentification à Streamlit/Python
    const authData = {
      username,
      password,
      timestamp: new Date().toISOString(),
      action: 'login'
    };
    
    try {
      // Communication bidirectionnelle avec Streamlit
      Streamlit.setComponentValue(authData);
    } catch (err) {
      setError('Erreur de communication avec le serveur');
      setLoading(false);
    }
  };

  // Appliquer le thème
  useEffect(() => {
    const theme = args?.theme || 'dark';
    document.documentElement.className = theme;
  }, [args?.theme]);

  return (
    <div className={`modern-auth-component ${args?.theme || 'dark'}`}>
      <LoginForm
        onSubmit={handleLogin}
        loading={loading}
        error={error || undefined}
        success={success}
      />
    </div>
  );
};

// Utiliser withStreamlitConnection pour la connexion automatique
const ConnectedAuthComponent = withStreamlitConnection(ModernAuthComponent);

// Point d'entrée simplifié
const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(<ConnectedAuthComponent />);
} else {
  console.error('Root container not found');
}