import React, { useState, useEffect } from 'react';

interface LoginFormProps {
  onSubmit: (username: string, password: string) => void;
  loading?: boolean;
  error?: string;
  success?: boolean;
}

interface FormErrors {
  username?: string;
  password?: string;
}

const LoginForm: React.FC<LoginFormProps> = ({ onSubmit, loading, error, success }) => {
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});
  const [touched, setTouched] = useState<{ username: boolean; password: boolean }>({
    username: false,
    password: false
  });

  // Validation en temps réel
  useEffect(() => {
    const newErrors: FormErrors = {};
    
    if (touched.username && !formData.username.trim()) {
      newErrors.username = 'Nom d\'utilisateur requis';
    } else if (touched.username && formData.username.length < 2) {
      newErrors.username = 'Au moins 2 caractères';
    }
    
    if (touched.password && !formData.password) {
      newErrors.password = 'Mot de passe requis';
    } else if (touched.password && formData.password.length < 3) {
      newErrors.password = 'Au moins 3 caractères';
    }
    
    setErrors(newErrors);
  }, [formData, touched]);

  const handleInputChange = (field: 'username' | 'password', value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleBlur = (field: 'username' | 'password') => {
    setTouched(prev => ({
      ...prev,
      [field]: true
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Marquer tous les champs comme touchés
    setTouched({ username: true, password: true });
    
    // Vérifier s'il y a des erreurs
    if (Object.keys(errors).length === 0 && formData.username && formData.password) {
      onSubmit(formData.username, formData.password);
    }
  };

  const isFormValid = Object.keys(errors).length === 0 && formData.username && formData.password;

  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-4">
      <div className="card w-full max-w-md bg-white shadow-2xl border border-gray-100 animate-slide-up">
        <div className="card-body p-8">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full mb-6 shadow-lg">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Authentification
            </h2>
            <p className="text-gray-600 text-sm">Accédez à votre espace sécurisé</p>
          </div>

          {/* Messages d'état */}
          {error && (
            <div className="alert alert-error mb-6 bg-red-50 border-red-200 animate-fade-in">
              <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-red-700">{error}</span>
            </div>
          )}

          {success && (
            <div className="alert alert-success mb-6 bg-green-50 border-green-200 animate-fade-in">
              <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-green-700">Connexion réussie !</span>
            </div>
          )}

          {/* Formulaire */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Champ Username */}
            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium text-gray-700">Nom d'utilisateur</span>
              </label>
              <div className="relative">
                <svg className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                <input
                  type="text"
                  placeholder="Saisissez votre nom d'utilisateur"
                  value={formData.username}
                  onChange={(e) => handleInputChange('username', e.target.value)}
                  onBlur={() => handleBlur('username')}
                  disabled={loading}
                  className={`input input-bordered w-full h-12 pl-12 bg-white border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 ${
                    errors.username ? 'border-red-400 focus:border-red-500 focus:ring-red-200' : ''
                  } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                />
              </div>
              {errors.username && (
                <label className="label">
                  <span className="label-text-alt text-red-600 flex items-center gap-1 text-sm">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {errors.username}
                  </span>
                </label>
              )}
            </div>

            {/* Champ Password */}
            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium text-gray-700">Mot de passe</span>
              </label>
              <div className="relative">
                <svg className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Saisissez votre mot de passe"
                  value={formData.password}
                  onChange={(e) => handleInputChange('password', e.target.value)}
                  onBlur={() => handleBlur('password')}
                  disabled={loading}
                  className={`input input-bordered w-full h-12 pl-12 pr-12 bg-white border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 ${
                    errors.password ? 'border-red-400 focus:border-red-500 focus:ring-red-200' : ''
                  } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 p-1 hover:bg-gray-100 rounded transition-colors"
                  disabled={loading}
                >
                  {showPassword ? 
                    <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                    </svg> : 
                    <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  }
                </button>
              </div>
              {errors.password && (
                <label className="label">
                  <span className="label-text-alt text-red-600 flex items-center gap-1 text-sm">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {errors.password}
                  </span>
                </label>
              )}
            </div>

            {/* Bouton de connexion */}
            <div className="form-control mt-8">
              <button
                type="submit"
                disabled={!isFormValid || loading}
                className={`btn w-full h-12 text-white font-medium rounded-lg transition-all flex items-center justify-center gap-2 ${
                  loading 
                    ? 'bg-blue-400 cursor-not-allowed' 
                    : isFormValid 
                      ? 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5' 
                      : 'bg-gray-300 cursor-not-allowed text-gray-500'
                }`}
              >
                {loading ? (
                  <>
                    <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Connexion...</span>
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
                    </svg>
                    <span>Se connecter</span>
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Comptes de test */}
          <div className="mt-8 p-4 bg-gray-50 border border-gray-200 rounded-lg">
            <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Comptes de test
            </h4>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between items-center py-1">
                <span className="font-mono px-2 py-1 bg-white border border-gray-300 rounded text-gray-700">admin</span>
                <span className="font-mono text-gray-500 select-all cursor-pointer hover:text-gray-700">admin123</span>
              </div>
              <div className="flex justify-between items-center py-1">
                <span className="font-mono px-2 py-1 bg-white border border-gray-300 rounded text-gray-700">user</span>
                <span className="font-mono text-gray-500 select-all cursor-pointer hover:text-gray-700">user123</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginForm;