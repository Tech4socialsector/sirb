import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    requiresRole?: (store: ReturnType<typeof useAuthStore>) => boolean
    title?: string
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/sirb',
    name: 'dashboard',
    component: () => import('@/pages/Dashboard.vue'),
    meta: { title: 'Dashboard' },
  },
  {
    path: '/sirb/my-projects',
    name: 'my-projects',
    component: () => import('@/pages/MyProjects.vue'),
    meta: {
      title: 'My IRB Projects',
      requiresRole: (s) => s.isStudent,
    },
  },
  {
    path: '/sirb/projects/:name',
    name: 'project-details',
    component: () => import('@/pages/ProjectDetails.vue'),
    props: true,
    meta: { title: 'Project Details' },
  },
  {
    path: '/sirb/review/mentor',
    name: 'mentor-projects',
    component: () => import('@/pages/MentorProjects.vue'),
    meta: {
      title: 'Mentor Worklist',
      requiresRole: (s) => s.isFacultyMentor || s.isAdmin,
    },
  },
  {
    path: '/sirb/review/primary',
    name: 'primary-reviewer-worklist',
    component: () => import('@/pages/ReviewerWorklist.vue'),
    props: { role: 'primary' },
    meta: {
      title: 'Primary Reviewer Worklist',
      requiresRole: (s) => s.isPrimaryReviewer || s.isAdmin,
    },
  },
  {
    path: '/sirb/review/secondary',
    name: 'secondary-reviewer-worklist',
    component: () => import('@/pages/ReviewerWorklist.vue'),
    props: { role: 'secondary' },
    meta: {
      title: 'Secondary Reviewer Worklist',
      requiresRole: (s) => s.isSecondaryReviewer || s.isAdmin,
    },
  },
  {
    path: '/sirb/admin',
    name: 'admin-console',
    component: () => import('@/pages/AdminConsole.vue'),
    meta: {
      title: 'IRB Admin Console',
      requiresRole: (s) => s.isAdmin,
    },
  },
  {
    path: '/sirb/admin/students',
    name: 'student-project-management',
    component: () => import('@/pages/StudentProjectManagement.vue'),
    meta: {
      title: 'Student & Project Management',
      requiresRole: (s) => s.isAdmin,
    },
  },
  {
    path: '/sirb/admin/reports',
    name: 'anchor-reports',
    component: () => import('@/pages/AnchorReports.vue'),
    meta: {
      title: 'Anchor Reports',
      requiresRole: (s) => s.isAnchor,
    },
  },
  {
    path: '/sirb/uploads/students',
    name: 'student-uploader',
    component: () => import('@/pages/StudentUploader.vue'),
    meta: {
      title: 'Upload Students',
      requiresRole: (s) => s.isAnchor,
    },
  },
  {
    path: '/sirb/uploads/faculty',
    name: 'faculty-uploader',
    component: () => import('@/pages/FacultyUploader.vue'),
    meta: {
      title: 'Upload Faculty',
      requiresRole: (s) => s.isAnchor,
    },
  },
  {
    path: '/sirb/profile',
    name: 'profile',
    component: () => import('@/pages/Profile.vue'),
    meta: { title: 'Profile' },
  },
  {
    path: '/sirb/unauthorized',
    name: 'unauthorized',
    component: () => import('@/pages/Unauthorized.vue'),
    meta: { title: 'Unauthorized' },
  },
  {
    path: '/sirb/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/pages/NotFound.vue'),
    meta: { title: 'Not Found' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()
  if (!authStore.initialized) {
    await authStore.load()
  }

  if (!authStore.currentUser) {
    // Session couldn't be resolved (likely logged out) — bounce to Frappe login,
    // preserving the intended destination for post-login redirect.
    window.location.href = `/login?redirect-to=${encodeURIComponent(to.fullPath)}`
    return false
  }

  if (to.meta.requiresRole && !to.meta.requiresRole(authStore)) {
    return { name: 'unauthorized' }
  }

  return true
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · SIRB` : 'SIRB'
})

export default router
