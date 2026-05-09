import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/DigitalEmployeeSkills.vue'),
  },
  {
    path: '/tools/quality-diagnosis',
    name: 'QualityDiagnosis',
    component: () => import('../views/QualityDiagnosisWorkbench.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
