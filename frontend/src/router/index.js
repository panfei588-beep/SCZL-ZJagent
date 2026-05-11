import { createRouter, createWebHistory } from 'vue-router'
import DigitalEmployeeSkills from '../views/DigitalEmployeeSkills.vue'
import QualityDiagnosisWorkbench from '../views/QualityDiagnosisWorkbench.vue'

const routes = [
  {
    path: '/',
    name: 'Skills',
    component: DigitalEmployeeSkills
  },
  {
    path: '/tools/quality-diagnosis',
    name: 'QualityDiagnosis',
    component: QualityDiagnosisWorkbench
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
