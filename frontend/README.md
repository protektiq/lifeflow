# LifeFlow Frontend

Next.js 16 frontend application for the LifeFlow multi-agent cognitive control system. Built with React 19, TypeScript, TailwindCSS, and Radix UI components.

## 🏗️ Architecture

The frontend is built using:
- **Next.js 16** - React framework with App Router
- **React 19** - UI library
- **TypeScript** - Type-safe JavaScript
- **TailwindCSS 4** - Utility-first CSS framework
- **Radix UI** - Accessible component primitives
- **Supabase Auth** - Authentication client
- **Axios** - HTTP client for API requests

## 📁 Project Structure

```
frontend/
├── app/                    # Next.js App Router pages
│   ├── auth/              # Authentication pages
│   │   ├── login/        # Login page
│   │   └── signup/       # Signup page
│   ├── dashboard/        # Dashboard pages
│   │   ├── page.tsx      # Main dashboard (Today's Plan)
│   │   ├── layout.tsx    # Dashboard layout with sidebar
│   │   ├── integrations/ # Calendar integration page
│   │   ├── planning/     # Planning history page
│   │   ├── data/         # Data/metrics page
│   │   └── notifications/ # Notifications page
│   ├── layout.tsx        # Root layout
│   ├── page.tsx          # Landing page
│   └── globals.css       # Global styles
├── components/            # React components
│   ├── ui/               # Radix UI components (shadcn/ui)
│   ├── DailyPlanView.tsx # Daily plan display component
│   ├── EnergyLevelInput.tsx # Energy level selector
│   ├── NotificationCenter.tsx # Notification display
│   ├── RawTasksView.tsx  # Task list display
│   ├── RemindersView.tsx # Reminders display
│   ├── TaskFeedback.tsx  # Task feedback component
│   ├── TaskManagerIntegration.tsx # Task manager sync UI
│   ├── DashboardSidebar.tsx # Navigation sidebar
│   └── ThemeProvider.tsx # Dark mode provider
├── src/
│   ├── lib/              # Utilities and API clients
│   │   ├── api.ts        # API client functions
│   │   └── supabase/     # Supabase client setup
│   └── types/            # TypeScript type definitions
│       ├── plan.ts       # Plan and energy level types
│       ├── task.ts       # Task types
│       └── notification.ts # Notification types
├── middleware.ts         # Route protection middleware
├── package.json          # Dependencies and scripts
├── tsconfig.json         # TypeScript configuration
├── tailwind.config.ts    # TailwindCSS configuration
└── next.config.ts        # Next.js configuration
```

## 🚀 Setup

### Prerequisites

- Node.js 18 or higher
- npm, yarn, pnpm, or bun

### Installation

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   # or
   yarn install
   # or
   pnpm install
   ```

3. **Configure environment variables:**
   
   Create a `.env.local` file in the frontend directory:
   ```bash
   # Supabase Configuration
   NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
   
   # Backend API URL
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

   > 💡 See [ENV_SETUP.md](../ENV_SETUP.md) for detailed instructions on obtaining these credentials.

4. **Start the development server:**
   ```bash
   npm run dev
   # or
   yarn dev
   # or
   pnpm dev
   ```

   The frontend will be available at `http://localhost:3000`

## 🎨 Features

### Pages

1. **Landing Page** (`/`)
   - Marketing/landing page with feature overview
   - Call-to-action for signup/login

2. **Authentication** (`/auth/login`, `/auth/signup`)
   - Email/password authentication
   - Google OAuth integration
   - Secure session management

3. **Dashboard** (`/dashboard`)
   - Main dashboard with today's plan
   - Energy level input
   - Daily plan generation and display
   - Task management

4. **Integrations** (`/dashboard/integrations`)
   - Google Calendar connection
   - Calendar sync functionality
   - Task manager integrations (Todoist, etc.)

5. **Planning** (`/dashboard/planning`)
   - View plan history
   - Past daily plans
   - Plan analytics

6. **Data** (`/dashboard/data`)
   - Sync metrics
   - Task statistics
   - Performance metrics

7. **Notifications** (`/dashboard/notifications`)
   - Notification center
   - Unread notifications
   - Notification history

### Components

- **DailyPlanView** - Displays and manages daily plans
- **EnergyLevelInput** - Energy level selector with history
- **NotificationCenter** - Real-time notification display
- **RawTasksView** - Task list with filtering and sorting
- **RemindersView** - Reminder management
- **TaskFeedback** - Task completion and feedback
- **TaskManagerIntegration** - Task manager sync interface
- **DashboardSidebar** - Navigation sidebar with menu items

## 🎯 Key Functionality

### Authentication
- Email/password login and signup
- Google OAuth integration
- Protected routes via middleware
- Session management with Supabase Auth

### Calendar Integration
- Connect Google Calendar
- Sync calendar events
- View sync status and metrics

### Daily Planning
- Set energy levels
- Generate AI-powered daily plans
- View and manage plans
- Task prioritization (critical/urgent flags)

### Task Management
- View extracted tasks from calendar
- Mark tasks as critical or urgent
- Provide feedback (done, snooze)
- Task details and editing

### Notifications
- Real-time notification display
- Unread notification count
- Dismiss notifications
- Notification history

### Task Manager Sync
- Connect external task managers (Todoist)
- Bidirectional sync
- Conflict resolution
- Sync status tracking

## 🎨 Styling

The frontend uses TailwindCSS 4 for styling with:
- Custom color palette (purple, pink, blue gradients)
- Dark mode support via `next-themes`
- Responsive design (mobile-first)
- Custom animations and transitions
- Accessible components from Radix UI

## 🔒 Security

- **Route Protection**: Middleware protects dashboard routes
- **JWT Tokens**: Authentication tokens stored securely
- **Environment Variables**: Sensitive data in `.env.local` (not committed)
- **CORS**: Configured to work with backend API

## 📱 Responsive Design

The application is fully responsive:
- Mobile-first approach
- Breakpoints: sm (640px), md (768px), lg (1024px), xl (1280px)
- Touch-friendly interactions
- Adaptive layouts

## 🌙 Dark Mode

Dark mode is supported via `next-themes`:
- System preference detection
- Manual toggle
- Persistent preference storage
- Smooth theme transitions

## 🧪 Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

### Code Structure

- **Components**: Reusable UI components in `/components`
- **Pages**: Route pages in `/app` (App Router)
- **API Client**: Centralized API calls in `/src/lib/api.ts`
- **Types**: TypeScript definitions in `/src/types`
- **Utilities**: Helper functions in `/src/lib`

## 🚢 Deployment

The frontend can be deployed to:
- **Vercel** (recommended for Next.js)
- **Netlify**
- **Any Node.js hosting platform**

See deployment documentation for details.

## 📝 Dependencies

Key dependencies (see `package.json` for full list):

- `next@16.0.1` - Next.js framework
- `react@19.2.0` - React library
- `react-dom@19.2.0` - React DOM
- `@supabase/ssr@0.7.0` - Supabase SSR client
- `@supabase/supabase-js@2.80.0` - Supabase client
- `axios@1.13.2` - HTTP client
- `tailwindcss@4` - CSS framework
- `@radix-ui/*` - UI component primitives
- `lucide-react@0.553.0` - Icon library
- `next-themes@0.4.6` - Theme management

## 🐛 Troubleshooting

### Common Issues

1. **Build errors**: Ensure Node.js version is 18+
2. **API connection errors**: Verify `NEXT_PUBLIC_API_URL` in `.env.local`
3. **Authentication errors**: Check Supabase credentials
4. **Styling issues**: Ensure TailwindCSS is properly configured

## 📚 Additional Resources

- [Main README](../README.md) - Project overview
- [Environment Setup Guide](../ENV_SETUP.md) - Detailed setup instructions
- [Running Guide](../RUNNING.md) - How to run the application
- [Next.js Documentation](https://nextjs.org/docs) - Next.js framework docs

---

**Made with ❤️ for LifeFlow**
