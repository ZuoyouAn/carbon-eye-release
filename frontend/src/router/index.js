import { createRouter, createWebHistory } from 'vue-router'
import { isAdmin, isLoggedIn, refreshMe } from '../stores/auth'
import HomeView from '../views/HomeView.vue'
const LoginView = () => import('../views/LoginView.vue')
const RegisterView = () => import('../views/RegisterView.vue')
const NovelView = () => import('../views/NovelView.vue')
const PostsView = () => import('../views/PostsView.vue')
const ArticlesView = () => import('../views/ArticlesView.vue')
const ArticleEditorView = () => import('../views/ArticleEditorView.vue')
const ProfileView = () => import('../views/ProfileView.vue')
const AdminView = () => import('../views/AdminView.vue')
const RoadmapView = () => import('../views/RoadmapView.vue')
const ProjectsView = () => import('../views/ProjectsView.vue')
const TimelineView = () => import('../views/TimelineView.vue')
const MessagesView = () => import('../views/MessagesView.vue')
const ChangelogView = () => import('../views/ChangelogView.vue')
const CarbonEyeView = () => import('../views/CarbonEyeView.vue')
const SecureGeometryView = () => import('../views/SecureGeometryView.vue')
const SecureGeometryPaperView = () => import('../views/SecureGeometryPaperView.vue')

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
    { path: '/human3', name: 'human3', component: () => import('../views/Human3View.vue') },
    { path: '/store', name: 'store', component: () => import('../views/StoreView.vue') },
    { path: '/chat', name: 'chat', component: () => import('../views/ChatView.vue'), meta: { requiresAuth: true } },
    { path: '/wasteland', name: 'wasteland', component: () => import('../views/WastelandView.vue') },
    { path: '/games', name: 'games', component: () => import('../views/GamesView.vue') },
    { path: '/games/swarm', name: 'swarm-game', component: () => import('../views/SwarmGameView.vue') },
    { path: '/games/winter', name: 'winter-game', component: () => import('../views/WinterGameView.vue') },
    { path: '/solar-system', name: 'solar-system', component: () => import('../views/SolarSystemView.vue') },
    { path: '/life-guide', name: 'life-guide', component: () => import('../views/LifeGuideView.vue') },
    { path: '/document-tools', name: 'document-tools', component: () => import('../views/DocumentToolsView.vue') },
    { path: '/crypto-lab', name: 'crypto-lab', component: () => import('../views/CryptoLabView.vue') },
    { path: '/secure-geometry', name: 'secure-geometry', component: SecureGeometryView },
    { path: '/secure-geometry/paper', name: 'secure-geometry-paper', component: SecureGeometryPaperView },
    { path: '/profile', name: 'profile', component: ProfileView, meta: { requiresAuth: true } },
    { path: '/admin', name: 'admin', component: AdminView, meta: { requiresAuth: true, requiresAdmin: true } },
    { path: '/admin/articles/new', name: 'article-editor', component: ArticleEditorView, meta: { requiresAuth: true, requiresAdmin: true } },
    { path: '/admin/articles/:id/edit', name: 'article-edit', component: ArticleEditorView, meta: { requiresAuth: true, requiresAdmin: true } },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('../views/NotFoundView.vue') },
  ],
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.path === from.path) return false
    return { top: 0 }
  },
})

router.afterEach((to) => {
  const titles = { home: '首页', human3: '四维成长测评', store: '数字商品 · 筹备中', projects: '项目', articles: '文章', novels: '小说', posts: '帖子', login: '登录', register: '注册', admin: '管理后台', profile: '个人中心', 'not-found': '页面不存在' }
  const extras = { chat: '聊天室', wasteland: '末世模拟器', 'solar-system': '太阳系图谱', 'life-guide': '高性价比人生指南', 'document-tools': '文档转换', 'crypto-lab': '密码算法实验室' }
  const games = { games: '游戏大厅', 'swarm-game': '星潮幸存者', 'winter-game': '寒境火种' }
  document.title = `${games[to.name] || extras[to.name] || titles[to.name] || '探索'} · 左右的Space`
})

router.beforeEach(async (to) => {
  if (to.meta.requiresAuth) await refreshMe()
  if (to.meta.requiresAuth && !isLoggedIn.value) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.meta.requiresAdmin && !isAdmin.value) {
    return { name: 'home' }
  }

  return true
})

export default router
