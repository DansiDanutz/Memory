# Multi-Environment Sync Guide
## Cursor + Claude Code + Replit

### 🔄 Current Setup
All three environments are synced through the same GitHub repository:
- **Repository**: https://github.com/DansiDanutz/Memory.git
- **Main Branch**: `main`
- **Frontend Location**: `/frontend`

### 📍 Environment URLs
- **Local (Claude Code/Cursor)**: http://localhost:5555
- **Replit**: Will auto-assign URL when deployed

### 🛠 Working in Each Environment

#### 1. **Claude Code (Current)**
```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5555
```

#### 2. **Cursor**
```bash
# Open the same folder in Cursor
cd frontend
npm install
npm run dev
# Will use the same port 5555
```

#### 3. **Replit**
- Import from GitHub: https://github.com/DansiDanutz/Memory.git
- Replit will auto-detect the Vite config
- Will run on Replit's assigned URL

### 📝 Sync Workflow

#### Before Starting Work:
```bash
git pull origin main
```

#### After Making Changes:
```bash
git add .
git commit -m "Your changes"
git push origin main
```

#### In Other Environments:
```bash
git pull origin main
npm install  # If package.json changed
```

### ⚙️ Configuration Files

#### Port Configuration (vite.config.js)
- Local: Port 5555 (fixed)
- Replit: Will override with environment port

#### Environment Variables
- Create `.env.local` for local secrets
- Use Replit Secrets for Replit environment
- Never commit `.env` files

### 🚀 Quick Commands

#### Start Development:
```bash
npm run dev
```

#### Build for Production:
```bash
npm run build
```

#### Run Tests:
```bash
npm run test
```

### ⚠️ Important Notes

1. **Always pull before starting work** to get latest changes
2. **Commit frequently** to avoid conflicts
3. **Use descriptive commit messages**
4. **Test in all environments** before major releases
5. **Keep node_modules in .gitignore**

### 🔧 Troubleshooting

#### Port Conflicts:
- The app is configured to use port 5555
- If busy, check `vite.config.js` to change

#### Dependency Issues:
```bash
rm -rf node_modules package-lock.json
npm install
```

#### Git Conflicts:
```bash
git stash
git pull origin main
git stash pop
# Resolve conflicts manually
```

### 📱 Current Features
- ✅ Modern UI with shadcn/ui
- ✅ Dark/Light theme
- ✅ WhatsApp-style memory app
- ✅ Gamification system
- ✅ Fixed port configuration
- ✅ Tailwind CSS v4 with PostCSS

### 🎯 Next Steps
1. Set up backend API
2. Configure WebSocket connections
3. Add authentication
4. Deploy to production