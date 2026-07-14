import { createRouter, createWebHistory } from 'vue-router'
import { authState, isAdmin } from '../stores/auth'
import HomeView from '../views/HomeView.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import NovelView from '../views/NovelView.vue'
import PostsView from '../views/PostsView.vue'
import ArticlesView from '../views/ArticlesView.vue'
import ArticleEditorView from '../views/ArticleEditorView.vue'
import ProfileView from '../views/ProfileView.vue'
import AdminView from '../views/AdminView.vue'
import RoadmapView from '../views/RoadmapView.vue'
import ProjectsView from '../views/ProjectsView.vue'
import TimelineView from '../views/TimelineView.vue'
import MessagesView from '../views/MessagesView.vue'
import ChangelogView from '../views/ChangelogView.vue'
import CarbonEyeView from '../views/CarbonEyeView.vue'
import SecureGeometryView from '../views/SecureGeometryView.vue'
import SecureGeometryPaperView from '../views/SecureGeometryPaperView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/login', name: 'login', component: LoginView },
    { path: '/register', name: 'register', component: RegisterView },
    { path: '/novels', name: 'novels', component: NovelView },
    { path: '/novels/:id', name: 'novel-detail', component: NovelView },
    { path: '/posts', name: 'posts', component: PostsView },
    { path: '/posts/:id', name: 'post-detail', component: PostsView },
    { path: '/articles', name: 'articles', component: ArticlesView },
    { path: '/articles/:id', name: 'article-detail', component: ArticlesView },
    { path: '/roadmap', name: 'roadmap', component: RoadmapView },
    { path: '/projects', name: 'projects', component: ProjectsView },
    { path: '/timeline', name: 'timeline', component: TimelineView },
    { path: '/messages', name: 'messages', component: MessagesView },
    { path: '/changelog', name: 'changelog', component: ChangelogView },
    { path: '/carbon-eye', name: 'carbon-eye', component: CarbonEyeView },
    { path: '/secure-geometry', name: 'secure-geometry', component: SecureGeometryView },
    { path: '/secure-geometry/paper', name: 'secure-geometry-paper', component: SecureGeometryPaperView },
    { path: '/profile', name: 'profile', component: ProfileView, meta: { requiresAuth: true } },
    { path: '/admin', name: 'admin', component: AdminView, meta: { requiresAuth: true, requiresAdmin: true } },
    { path: '/admin/articles/new', name: 'article-editor', component: ArticleEditorView, meta: { requiresAuth: true, requiresAdmin: true } },
    { path: '/admin/articles/:id/edit', name: 'article-edit', component: ArticleEditorView, meta: { requiresAuth: true, requiresAdmin: true } },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !authState.user) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.meta.requiresAdmin && !isAdmin.value) {
    return { name: 'home' }
  }

  return true
})

export default router
