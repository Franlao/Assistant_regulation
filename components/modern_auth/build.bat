@echo off
echo Building Modern Auth Component...

echo Installing dependencies...
npm install

if %ERRORLEVEL% neq 0 (
    echo Failed to install dependencies
    exit /b 1
)

echo Installing TypeScript preset...
npm install --save-dev @babel/preset-typescript

if %ERRORLEVEL% neq 0 (
    echo Failed to install TypeScript preset
    exit /b 1
)

echo Building for production...
npm run build

if %ERRORLEVEL% neq 0 (
    echo Failed to build
    exit /b 1
)

echo Build completed successfully!
echo Files are ready in dist/ directory