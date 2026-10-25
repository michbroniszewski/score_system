import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'
import CompetitionLayout from './views/CompetitionLayout.vue'
import CompetitionList from './views/CompetitionList.vue'
import MatchesView from './views/MatchesView.vue'
import MatchView from './views/MatchView.vue'
import PlayoffView from './views/PlayoffView.vue'
import RosterView from './views/RosterView.vue'
import StandingsView from './views/StandingsView.vue'
import StatsView from './views/StatsView.vue'
import TeamsView from './views/TeamsView.vue'

const publicRoutes: RouteRecordRaw[] = [
  { path: '/', name: 'competitions', component: CompetitionList },
  {
    path: '/competitions/:slug',
    component: CompetitionLayout,
    props: true,
    children: [
      { path: '', name: 'standings', component: StandingsView, props: true },
      { path: 'matches', name: 'matches', component: MatchesView, props: true },
      { path: 'teams', name: 'teams', component: TeamsView, props: true },
      { path: 'teams/:teamId', name: 'roster', component: RosterView, props: true },
      { path: 'stats', name: 'stats', component: StatsView, props: true },
      { path: 'playoff', name: 'playoff', component: PlayoffView, props: true },
      { path: 'matches/:matchId', name: 'match', component: MatchView, props: true },
    ],
  },
]

// The admin panel edits the local database, so the read-only Pages build leaves it out.
const adminRoutes: RouteRecordRaw[] = [
  { path: '/admin', name: 'admin', component: () => import('./admin/AdminHome.vue') },
  {
    path: '/admin/competitions/:slug',
    name: 'admin-competition',
    component: () => import('./admin/AdminCompetition.vue'),
    props: true,
  },
  {
    path: '/admin/competitions/:slug/teams/:teamId',
    name: 'admin-roster',
    component: () => import('./admin/AdminRoster.vue'),
    props: true,
  },
  {
    path: '/admin/competitions/:slug/matches/:matchId',
    name: 'admin-match',
    component: () => import('./admin/AdminMatch.vue'),
    props: true,
  },
]

// The condition is spelled out (not `staticData` from the client) so that the build can
// drop the admin views from the Pages bundle entirely.
export const routes =
  import.meta.env.VITE_STATIC_DATA === 'true' ? publicRoutes : [...publicRoutes, ...adminRoutes]

// Hash history (#/...): GitHub Pages serves static files only, so other paths would be 404s.
export const router = createRouter({ history: createWebHashHistory(), routes })
