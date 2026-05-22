import { createRouter, createWebHistory } from "vue-router";
import LoginView from "../views/LoginView.vue";
import CourseView from "../views/CourseView.vue";
import ChoiceView from "../views/ChoiceView.vue";
import StatsView from "../views/StatsView.vue";
import ProfileView from "../views/ProfileView.vue";
import CrossChoiceView from "../views/CrossChoiceView.vue";
import StudentManagementView from "../views/StudentManagementView.vue";
import CourseManagementView from "../views/CourseManagementView.vue";

const routes = [
  { path: "/", redirect: "/login" },
  { path: "/login", name: "login", component: LoginView },
  { path: "/profile", name: "profile", component: ProfileView },
  { path: "/courses", name: "courses", component: CourseView },
  { path: "/choice", name: "choice", component: ChoiceView },
  { path: "/cross-choice", name: "cross-choice", component: CrossChoiceView },
  { path: "/stats", name: "stats", component: StatsView },
  { path: "/student-management", name: "student-management", component: StudentManagementView },
  { path: "/course-management", name: "course-management", component: CourseManagementView }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;
