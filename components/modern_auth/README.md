# Modern Authentication Component

Composant d'authentification moderne pour Streamlit utilisant React + Tailwind CSS.

## Fonctionnalités

- Interface moderne avec glassmorphism
- Validation en temps réel des champs
- Communication bidirectionnelle Python ↔ JavaScript
- Animations fluides et feedback visuel
- Support thème sombre/clair
- Icons React (Feather Icons)
- Responsive design

## Structure du projet

```
modern_auth/
├── package.json          # Dépendances Node.js
├── webpack.config.js     # Configuration Webpack
├── tailwind.config.js    # Configuration Tailwind CSS
├── .babelrc             # Configuration Babel
├── build.bat            # Script de build Windows
├── public/
│   └── index.html       # Template HTML
├── src/
│   ├── index.tsx        # Point d'entrée + communication Streamlit
│   ├── LoginForm.tsx    # Composant formulaire principal
│   └── styles.css       # Styles Tailwind + classes custom
└── dist/                # Build output (généré)
```

## Installation et Build

### 1. Installer Node.js
Téléchargez et installez Node.js depuis https://nodejs.org/

### 2. Build du composant
```bash
cd components/modern_auth
./build.bat
```

Ou manuellement :
```bash
npm install
npm run build
```

### 3. Mode développement
Pour développer avec hot reload :
```bash
npm run dev
```

Le composant sera disponible à http://localhost:3001

## Utilisation dans Streamlit

### Configuration simple
```python
from components.modern_auth_integration import render_modern_login
from components.auth_components import SimpleAuth

# Backend d'authentification
auth_backend = SimpleAuth()

# Afficher le login moderne
if render_modern_login(auth_backend, theme="dark"):
    st.success("Utilisateur connecté!")
```

### Utilisation avancée
```python
from components.modern_auth_component import ModernAuthManager

auth_manager = ModernAuthManager(auth_backend)

if auth_manager.render_login():
    user_info = auth_manager.get_user_info()
    st.write(f"Connecté: {user_info['username']}")
```

## Migration depuis l'ancien système

Remplacez dans vos fichiers :

```python
# Ancien
from components.auth_components import render_login_form, require_authentication

# Nouveau
from components.modern_auth_integration import render_modern_auth_page, require_modern_authentication
```

## Technologies utilisées

- **React 18** - Framework UI
- **Tailwind CSS** - Framework CSS utility-first
- **React Icons** - Bibliothèque d'icônes (Feather Icons)
- **Webpack** - Bundler module
- **Babel** - Transpileur JavaScript
- **Streamlit Component Library** - Communication bidirectionnelle

## Personnalisation

### Thèmes
Le composant supporte les thèmes "dark" et "light" :

```python
auth_manager.render_login(theme="light")
```

### Styles
Modifiez `src/styles.css` pour personnaliser l'apparence.

### Configuration Tailwind
Éditez `tailwind.config.js` pour ajouter couleurs, animations, etc.

## Dépannage

### Build fails
- Vérifiez que Node.js est installé : `node --version`
- Supprimez `node_modules/` et relancez `npm install`

### Composant ne s'affiche pas
- Vérifiez que le build a créé des fichiers dans `dist/`
- Assurez-vous que `_RELEASE = True` dans `modern_auth_component.py`

### Mode développement
Pour le développement avec hot reload :
1. Changez `_RELEASE = False` dans `modern_auth_component.py`
2. Lancez `npm run start` pour démarrer le serveur de dev
3. Le composant se connectera à http://localhost:3001